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

  return mod;
};
