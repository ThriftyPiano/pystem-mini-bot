// PySTEM: programmable surface / motor-imbalance model for the Mini Bot.
//
// No UI: drive it from a script (or the browser console) inside the GEARS
// frame, or from the embedding page with
//   iframe.contentWindow.postMessage({type: 'minibot-physics', config: {...}}, origin)
//
//   minibotPhysics.set({surface: 'carpet'})                      // preset
//   minibotPhysics.set({surface: {stallDps: 40}})                // tweak the current surface
//   minibotPhysics.set({motors: {left: {power: 0.9},             // left motor 10% weak
//                                right: {friction: 1.3}}})       // right side drags more
//   minibotPhysics.set({seed: 42})                               // deterministic noise
//   minibotPhysics.reset()                                       // back to the ideal wheel
//   minibotPhysics.get()                                         // resolved config
//
// Surface parameters (apply to both wheels, scaled per motor):
//   grip         wheel-tyre friction multiplier on the configured wheelFriction
//   rollingDps   wheel deg/s lost to rolling resistance (an open-loop servo
//                slows under load; the on-device velocity loop only partly
//                hides this)
//   stallDps     commanded wheel deg/s below which the wheel does not move at
//                all (static friction / carpet pile)
//   lagMs        first-order time constant of the wheel speed response
//   noise        fractional speed jitter per physics frame (surface roughness)
//   linearDamping / angularDamping   Ammo damping on the chassis body
//                (carpet pile resists sliding and pivoting)
//
// Per-motor parameters ('left'/'outA', 'right'/'outB'):
//   power        0..1+  speed and torque scale (a weak motor)
//   friction     resistance scale for that side's drivetrain: multiplies the
//                surface's rollingDps and stallDps for this wheel
//
// NOTE: `power` scales the achieved wheel speed open-loop, i.e. it models a
// weak motor with NO working encoder feedback. The real robot's per-wheel
// velocity loop compensates most of a constant imbalance by itself, so the
// same `power` figure produces more heading drift here than on hardware.
// motor_pair's yaw-hold gains are tuned against the real robot (its sluggish
// inner loops oscillate at gains this instant-response model tolerates);
// judge straight-line drift under imbalance qualitatively, not in degrees.
//
// Wheel.js calls applyToWheel() every physics frame while a wheel is driven
// and syncWheel() every frame to push grip/damping changes into Ammo.

var minibotPhysics = (function() {
  var SURFACES = {
    ideal: {
      grip: 1.0, rollingDps: 0, stallDps: 0, lagMs: 0, noise: 0,
      linearDamping: 0, angularDamping: 0
    },
    hardwood: {
      grip: 0.6, rollingDps: 4, stallDps: 6, lagMs: 60, noise: 0.015,
      linearDamping: 0.01, angularDamping: 0.01
    },
    carpet: {
      grip: 1.2, rollingDps: 18, stallDps: 25, lagMs: 160, noise: 0.05,
      linearDamping: 0.2, angularDamping: 0.8
    }
  };
  var MOTOR_DEFAULT = { power: 1.0, friction: 1.0 };
  var PORT_ALIAS = { left: 'outA', right: 'outB', outA: 'outA', outB: 'outB' };

  var state = {
    surfaceName: 'ideal',
    surface: Object.assign({}, SURFACES.ideal),
    motors: {
      outA: Object.assign({}, MOTOR_DEFAULT),
      outB: Object.assign({}, MOTOR_DEFAULT)
    },
    seed: 1
  };
  var generation = 0;
  var rngState = 1;

  function rand() {
    // LCG in [-1, 1): deterministic runs for the headless tests.
    rngState = (rngState * 1664525 + 1013904223) >>> 0;
    return rngState / 2147483648 - 1;
  }

  function set(cfg) {
    cfg = cfg || {};
    if (typeof cfg.surface == 'string') {
      if (!SURFACES[cfg.surface]) { throw new Error('Unknown surface: ' + cfg.surface); }
      state.surfaceName = cfg.surface;
      state.surface = Object.assign({}, SURFACES[cfg.surface]);
    } else if (typeof cfg.surface == 'object' && cfg.surface !== null) {
      state.surfaceName = 'custom';
      Object.assign(state.surface, cfg.surface);
    }
    if (cfg.motors) {
      for (var key in cfg.motors) {
        var port = PORT_ALIAS[key];
        if (!port) { throw new Error('Unknown motor: ' + key + " (use 'left'/'right')"); }
        Object.assign(state.motors[port], cfg.motors[key]);
      }
    }
    if (typeof cfg.seed == 'number') { state.seed = cfg.seed; }
    rngState = state.seed >>> 0 || 1;
    generation++;
    return get();
  }

  function reset() {
    state.surfaceName = 'ideal';
    state.surface = Object.assign({}, SURFACES.ideal);
    state.motors.outA = Object.assign({}, MOTOR_DEFAULT);
    state.motors.outB = Object.assign({}, MOTOR_DEFAULT);
    generation++;
    return get();
  }

  function get() {
    return JSON.parse(JSON.stringify({
      surface: Object.assign({ name: state.surfaceName }, state.surface),
      motors: state.motors,
      seed: state.seed
    }));
  }

  function active() {
    return state.surfaceName != 'ideal'
      || state.motors.outA.power != 1 || state.motors.outA.friction != 1
      || state.motors.outB.power != 1 || state.motors.outB.friction != 1;
  }

  // Called from Wheel.setMotorSpeed with the ramped setpoint in deg/s
  // (sign = commanded direction). Returns the speed the joint motor should
  // chase and the force behind it.
  function applyToWheel(wheel, dps, delta) {
    var motor = state.motors[wheel.port] || MOTOR_DEFAULT;
    var s = state.surface;

    var cmd = dps * motor.power;
    var sign = cmd > 0 ? 1 : -1;
    if (Math.abs(cmd) < s.stallDps * motor.friction) {
      cmd = 0;   // static friction / carpet pile holds the wheel
    } else {
      var loaded = Math.abs(cmd) - s.rollingDps * motor.friction;
      cmd = sign * Math.max(0, loaded);
    }
    if (s.noise > 0 && cmd !== 0) {
      cmd *= 1 + s.noise * rand();
    }
    if (s.lagMs > 0) {
      if (wheel._mbpSpeed === undefined) { wheel._mbpSpeed = 0; }
      var alpha = Math.min(1, delta / s.lagMs);
      wheel._mbpSpeed += (cmd - wheel._mbpSpeed) * alpha;
      cmd = wheel._mbpSpeed;
    } else {
      wheel._mbpSpeed = cmd;
    }
    return {
      speed: cmd,
      force: wheel.MOTOR_POWER_DEFAULT * motor.power
    };
  }

  // Called from Wheel.render: pushes grip and body damping into Ammo when
  // the config changes (cheap generation check per frame).
  function syncWheel(wheel) {
    if (wheel._mbpGeneration === generation) { return; }
    wheel._mbpGeneration = generation;
    wheel._mbpSpeed = 0;
    try {
      var imp = wheel.mesh.physicsImpostor;
      if (imp && imp.physicsBody) {
        imp.physicsBody.setFriction(wheel.options.friction * state.surface.grip);
      }
      var bodyImp = wheel.parent && wheel.parent.physicsImpostor;
      if (bodyImp && bodyImp.physicsBody) {
        bodyImp.physicsBody.setDamping(state.surface.linearDamping, state.surface.angularDamping);
      }
    } catch (e) {
      console.log('minibotPhysics sync failed: ' + e);
    }
  }

  return {
    set: set,
    reset: reset,
    get: get,
    active: active,
    applyToWheel: applyToWheel,
    syncWheel: syncWheel,
    surfaces: SURFACES
  };
})();
window.minibotPhysics = minibotPhysics;
