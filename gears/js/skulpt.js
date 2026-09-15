var skulpt = new function() {
  var self = this;

  this.externalLibs = {
    './ev3dev2/__init__.py': false,
    './ev3dev2/motor.py': 'ev3dev2/motor.py?v=d118b16a',
    './ev3dev2/sound.py': 'ev3dev2/sound.py?v=ec3085ff',
    './ev3dev2/button.py': 'ev3dev2/button.py?v=a7f892ad',
    './ev3dev2/sensor/__init__.py': 'ev3dev2/sensor/__init__.py?v=6d1f054c',
    './ev3dev2/sensor/lego.py': 'ev3dev2/sensor/lego.py?v=9fa3d991',
    './ev3dev2/sensor/virtual.py': 'ev3dev2/sensor/virtual.py?v=db93c480',
    './simPython.js': 'js/simPython.js?v=1b9bc620',
    './pybricks/__init__.py': false,
    './pybricks/parameters.py': 'pybricks/parameters.py?v=2db482b9',
    './pybricks/tools.py': 'pybricks/tools.py?v=20eafcfc',
    './pybricks/hubs.py': 'pybricks/hubs.py?v=7fa5cb11',
    './pybricks/ev3devices.py': 'pybricks/ev3devices.py?v=5768e95d',
    './pybricks/robotics.py': 'pybricks/robotics.py?v=bf287d71',
    './ev3dev2/Training_Wheels.py': 'ev3dev2/Training_Wheels.py?v=ad06cf56',
    // PySTEM Mini Bot SDK. motor_pair.py is the real on-device file from
    // examples/; the rest are simulator builds of the same API (minibot/).
    './config.py': 'minibot/config.py',
    './motor.py': 'minibot/motor.py',
    './motor_pair.py': '../examples/sdk_motor_pair.py',
    './orientation.py': 'minibot/orientation.py',
    './color_sensor.py': 'minibot/color_sensor.py',
    './head.py': 'minibot/head.py',
    './wonder_echo.py': 'minibot/wonder_echo.py',
    './minibot_sim.js': 'js/minibotSim.js',
    './machine.py': 'minibot/machine.py',
  };
  this.preloadedLibs = {};

  // Run on page load
  this.init = function() {
    Sk.configure({
      output: self.outf,
      read: self.builtinRead,
      __future__: Sk.python3
    });
    Sk.execLimit = 5000;
    self.patchTimeModule();

    self.preload();
  };

  // Run program
  this.runPython = function(prog) {
    if (typeof self.hardInterrupt != 'undefined') {
      delete self.hardInterrupt;
    }
    if (self.running == true) {
      return;
    }
    self.running = true;

    var myPromise = Sk.misceval.asyncToPromise(
      function() {
        return Sk.importMainWithBody("<stdin>", false, prog, true);
      },
      {
        '*': self.interruptHandler
      }
    );
    var resetExecStart = setInterval(function(){Sk.execStart = Date();}, 2000);
    myPromise.then(
      function(mod) {
        self.running = false;
        clearInterval(resetExecStart);
        simPanel.setRunIcon('run');
      },
      function(err) {
        self.running = false;
        if (err instanceof Sk.builtin.ExternalError) {
          console.log(err.toString());
        } else {
          simPanel.consoleWriteErrors(err.toString());
        }
        clearInterval(resetExecStart);
        simPanel.setRunIcon('run');
      }
    );
  };

  // InterruptHandler
  this.interruptHandler = function (susp) {
    if (self.hardInterrupt === true) {
      delete self.hardInterrupt;
      throw new Sk.builtin.ExternalError('aborted execution');
    } else {
      return null;
    }
  };

  // Skulpt evals a builtin JS module's source and takes the value of the
  // trailing `$builtinmodule` expression, so appending a wrapper that
  // rebinds $builtinmodule extends the module.
  this.patchTimeModule = function() {
    // Skulpt ships a placeholder `config` package that raises
    // NotImplementedError and would shadow minibot/config.py.
    delete Sk.builtinFiles.files['src/lib/config/__init__.py'];

    let key = 'src/lib/time.js';
    if (Sk.builtinFiles.files[key].indexOf('ticks_ms') != -1) {
      return;
    }
    Sk.builtinFiles.files[key] += `
var $minibotOrigTime = $builtinmodule;
$builtinmodule = function() {
  var mod = $minibotOrigTime.apply(this, arguments);
  mod.ticks_ms = new Sk.builtin.func(function() {
    return new Sk.builtin.int_(Math.floor(performance.now()));
  });
  mod.ticks_us = new Sk.builtin.func(function() {
    return new Sk.builtin.int_(Math.floor(performance.now() * 1000));
  });
  mod.ticks_diff = new Sk.builtin.func(function(a, b) {
    return new Sk.builtin.int_(Sk.ffi.remapToJs(a) - Sk.ffi.remapToJs(b));
  });
  mod.ticks_add = new Sk.builtin.func(function(a, b) {
    return new Sk.builtin.int_(Sk.ffi.remapToJs(a) + Sk.ffi.remapToJs(b));
  });
  mod.sleep_ms = new Sk.builtin.func(function(ms) {
    return Sk.misceval.callsimOrSuspendArray(mod.sleep, [new Sk.builtin.float_(Sk.ffi.remapToJs(ms) / 1000)]);
  });
  mod.sleep_us = new Sk.builtin.func(function(us) {
    return Sk.misceval.callsimOrSuspendArray(mod.sleep, [new Sk.builtin.float_(Sk.ffi.remapToJs(us) / 1000000)]);
  });
  return mod;
};
`;
  };

  // Write to stdout
  this.outf = function (text) {
    simPanel.consoleWrite(text);
  };

  // Files preloader
  this.preload = function () {
    function fetchPreload(key, url){
      fetch(url)
        .then(function(r){
          return r.text();
        })
        .then(function(r){
          self.preloadedLibs[key] = r;
        });
    }

    for (key in self.externalLibs) {
      if (self.externalLibs[key] === false) {
        self.preloadedLibs[key] = '';
      } else {
        fetchPreload(key, self.externalLibs[key]);
      }
    }
  };

  // File loader
  this.builtinRead = function (filename) {
    let searchModule = filename;
    if (searchModule.startsWith('./')) {
      searchModule = searchModule.substring(2);
    }
    if (filesManager.files[searchModule] !== undefined) {
      return filesManager.files[searchModule];
    }

    if (Sk.builtinFiles === undefined || Sk.builtinFiles["files"][filename] === undefined) {
      if (filename in self.preloadedLibs) {
        return self.preloadedLibs[filename];
      } else if (filename in self.externalLibs) {
        return Sk.misceval.promiseToSuspension(
          fetch(self.externalLibs[filename])
            .then(r => r.text())
        );
      } else {
        throw "File not found: '" + filename + "'";
      }
    }
    return Sk.builtinFiles["files"][filename];
  };
}

// Init class
skulpt.init();
