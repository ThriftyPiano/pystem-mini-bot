// Speech-command recognizer for the browser, sharing the device's pipeline.
//
// speech-commands/mfcc.js (Emscripten) contains the whole on-device chain:
// MFCC front end -> NNoM keyword-spotting base CNN -> quantized int8
// classifier loaded with init_model(). So a model trained on the Speech
// page runs here bit-for-bit as it does on the StickS3 - no TensorFlow.js
// needed. This file wraps that in a microphone loop that mirrors
// speech-firmware/device/main.py: recognise the last ~1 s of audio every
// 160 ms, accept a word above the probability threshold, debounce 1 s.
//
// Usage (after mfcc.js has loaded):
//   await SpeechRuntime.ready();
//   SpeechRuntime.loadModel(payload);          // the speech-model:<id> object
//   await SpeechRuntime.start({onCommand, onResult});
//   SpeechRuntime.stop();
//   SpeechRuntime.injectAudio(float32Samples); // tests: feed audio without a mic
var SpeechRuntime = (function() {
  var SAMPLE_RATE = 16000;
  var INPUT_COUNT = 62 * 256;      // ~0.976 s, what predict() consumes
  var STEP_MS = 160;               // 5120 samples, the device's slide step
  var OTHER = '[OTHER]';

  var labels = [];
  var audioInput = null;           // int16 buffer in WASM memory
  var weightPtr = null, biasPtr = null;
  var ring = new Float32Array(INPUT_COUNT);
  var ringFilled = 0;
  var listening = false;
  var stream = null, context = null, processor = null, timer = null;
  var lastCommandAt = -1e9;
  var opts = {};
  var wasmReady = null;

  function ready() {
    if (!wasmReady) {
      wasmReady = new Promise(function(resolve) {
        if (typeof Module === 'undefined') {
          throw new Error('speech-commands/mfcc.js must be loaded before runtime.js');
        }
        if (Module.calledRun) {
          resolve();
        } else {
          var prev = Module.onRuntimeInitialized;
          Module.onRuntimeInitialized = function() {
            if (prev) prev();
            resolve();
          };
        }
      });
    }
    return wasmReady;
  }

  function b64ToBytes(b64) {
    var bin = atob(b64), out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  // payload: the speech-model:<id> object from the Speech page
  // (labels + the same base64 bytes speech_model.py embeds).
  function loadModel(payload) {
    var bytes = b64ToBytes(payload.data);
    var numLabels = bytes[0];
    var weightDecBit = bytes[1], biasDecBit = bytes[2], biasShift = bytes[3], outputShift = bytes[4];
    var numFeatures = 576;
    var weightLen = numFeatures * numLabels;
    if (bytes.length !== 5 + weightLen + numLabels) {
      throw new Error('speech model payload has the wrong size');
    }
    if (weightPtr) { Module._free(weightPtr); Module._free(biasPtr); }
    weightPtr = Module._malloc(weightLen);
    biasPtr = Module._malloc(numLabels);
    Module.HEAP8.set(new Int8Array(bytes.buffer, 5, weightLen), weightPtr);
    Module.HEAP8.set(new Int8Array(bytes.buffer, 5 + weightLen, numLabels), biasPtr);
    Module.ccall('init_model', null,
      ['number', 'number', 'number', 'number', 'number', 'number', 'number'],
      [numLabels, weightPtr, weightDecBit, biasPtr, biasDecBit, biasShift, outputShift]);
    labels = payload.labels.slice();
    if (labels.length !== numLabels) {
      throw new Error('speech model labels do not match its weights');
    }
    ringFilled = 0;
    return labels;
  }

  // Run the classifier over the last ~1 s in the ring buffer.
  function predictNow() {
    if (!labels.length || ringFilled < INPUT_COUNT) return null;
    if (!audioInput) audioInput = Module._malloc(INPUT_COUNT * 2);
    var i16 = new Int16Array(INPUT_COUNT);
    for (var i = 0; i < INPUT_COUNT; i++) {
      var v = Math.max(-1, Math.min(1, ring[i]));
      i16[i] = Math.round(v * 32767);
    }
    Module.HEAP16.set(i16, audioInput >> 1);
    var result = Module.ccall('predict', 'number', ['number'], [audioInput]);
    var index = Math.floor(result / 1000), prob = (result % 1000) / 100;
    return {label: labels[index], prob: prob, index: index};
  }

  function pushAudio(chunk) {
    var n = chunk.length;
    if (n >= INPUT_COUNT) {
      ring.set(chunk.subarray(n - INPUT_COUNT));
      ringFilled = INPUT_COUNT;
      return;
    }
    ring.copyWithin(0, n);
    ring.set(chunk, INPUT_COUNT - n);
    ringFilled = Math.min(INPUT_COUNT, ringFilled + n);
  }

  function tick() {
    var r = predictNow();
    if (!r) return;
    if (opts.onResult) opts.onResult(r);
    var threshold = opts.threshold === undefined ? 0.7 : opts.threshold;
    var debounce = opts.debounceMs === undefined ? 1000 : opts.debounceMs;
    if (r.label !== OTHER && r.prob >= threshold) {
      var now = performance.now();
      if (now - lastCommandAt >= debounce) {
        lastCommandAt = now;
        if (opts.onCommand) opts.onCommand(r.label, r.prob);
      }
    }
  }

  async function start(options) {
    opts = options || {};
    if (listening) return;
    if (!labels.length) throw new Error('loadModel() first');
    stream = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
    context = new AudioContext({sampleRate: SAMPLE_RATE});
    var source = context.createMediaStreamSource(stream);
    processor = context.createScriptProcessor(512, 1, 1);
    processor.onaudioprocess = function(e) {
      pushAudio(e.inputBuffer.getChannelData(0));
    };
    source.connect(processor);
    processor.connect(context.destination);
    ringFilled = 0;
    lastCommandAt = -1e9;
    listening = true;
    timer = setInterval(tick, STEP_MS);
  }

  function stop() {
    listening = false;
    if (timer) { clearInterval(timer); timer = null; }
    if (processor) { processor.disconnect(); processor = null; }
    if (stream) { stream.getAudioTracks().forEach(function(t) { t.stop(); }); stream = null; }
    if (context) { context.close(); context = null; }
  }

  // Tests / other sources: feed 16 kHz float samples as if from the mic and
  // evaluate immediately. Returns the classifier result for the last second.
  function injectAudio(samples, options) {
    if (options) opts = options;
    pushAudio(samples);
    var r = predictNow();
    if (r && opts.onResult) opts.onResult(r);
    if (r && r.label !== OTHER && r.prob >= (opts.threshold === undefined ? 0.7 : opts.threshold) && opts.onCommand) {
      opts.onCommand(r.label, r.prob);
    }
    return r;
  }

  return {ready: ready, loadModel: loadModel, start: start, stop: stop, injectAudio: injectAudio,
          predictNow: predictNow, isListening: function() { return listening; },
          labels: function() { return labels.slice(); }};
})();
