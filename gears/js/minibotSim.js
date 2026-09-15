// Skulpt module `minibot_sim`: the page-side bridge the Mini Bot shim
// modules use for things GEARS has no component for.
//   voice_command() -> str  : next word typed into the Voice box, or ''
//   head_moved(pan, tilt)   : report simulated head angles to the console
var $builtinmodule = function(name) {
  var mod = {};

  mod.voice_command = new Sk.builtin.func(function() {
    var q = window.minibotVoiceQueue || [];
    if (q.length == 0) {
      return new Sk.builtin.str('');
    }
    return new Sk.builtin.str(q.shift());
  });

  mod.head_moved = new Sk.builtin.func(function(pan, tilt) {
    if (typeof simPanel != 'undefined') {
      simPanel.consoleWrite('[head] pan ' + Sk.ffi.remapToJs(pan) + ' tilt ' + Sk.ffi.remapToJs(tilt) + '\n');
    }
    return Sk.builtin.none.none$;
  });

  // Speech commands recognised by speech-commands/runtime.js on the page
  // (window.minibotSpeech, set up by index.html when a model is chosen).
  function speech() { return window.minibotSpeech || null; }
  mod.speech_command = new Sk.builtin.func(function() {
    var q = window.minibotSpeechQueue || [];
    return new Sk.builtin.str(q.length ? q.shift() : '');
  });
  mod.speech_labels = new Sk.builtin.func(function() {
    var sp = speech();
    return Sk.ffi.remapToPy(sp ? sp.labels() : []);
  });
  mod.speech_start = new Sk.builtin.func(function() {
    var sp = speech();
    if (!sp) return Sk.builtin.bool.false$;
    sp.start();
    return Sk.builtin.bool.true$;
  });
  mod.speech_stop = new Sk.builtin.func(function() {
    var sp = speech();
    if (sp) sp.stop();
    return Sk.builtin.none.none$;
  });
  mod.speech_is_listening = new Sk.builtin.func(function() {
    var sp = speech();
    return sp && sp.isListening() ? Sk.builtin.bool.true$ : Sk.builtin.bool.false$;
  });

  // machine.Pin writes: console line + the page's LED indicator
  mod.pin_changed = new Sk.builtin.func(function(pin, value) {
    var p = Sk.ffi.remapToJs(pin), v = Sk.ffi.remapToJs(value);
    if (typeof simPanel != 'undefined') {
      simPanel.consoleWrite('[pin ' + p + '] ' + (v ? 'HIGH' : 'LOW') + '\n');
    }
    if (typeof window.minibotPinChanged == 'function') {
      window.minibotPinChanged(p, v);
    }
    return Sk.builtin.none.none$;
  });

  return mod;
};
