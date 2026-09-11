// MicroPython bindings for the keyword-spotting model, exposed as the
// `speech_commands` module.
#include "py/runtime.h"
#include "py/mpthread.h"

void kws_set_debug(int val);
void kws_init(void* buffer);
int32_t kws_predict(int16_t* audio_input, int num_bytes, int bias, int gain);
void kws_export_mfcc(int8_t* buffer);
void kws_normalize(float* input, int8_t* output);
void kws_compute_mfcc(int16_t* audio_frame, float* mfcc_output);
int32_t kws_predict2(int8_t* input);
void kws_normalize_audio(int16_t* input, int16_t* output, int len,
  int bias, int gain);

static mp_obj_t set_debug(mp_obj_t val) {
  kws_set_debug(mp_obj_get_int(val));
  return mp_obj_new_int(0);
}

static mp_obj_t init(mp_obj_t buffer) {
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(buffer, &bufinfo, MP_BUFFER_READ);
  kws_init(bufinfo.buf);
  return mp_obj_new_int(0);
}

static mp_obj_t predict(mp_obj_t audio_input, mp_obj_t bias, mp_obj_t gain) {
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(audio_input, &bufinfo, MP_BUFFER_READ);
  int bias_i = mp_obj_get_int(bias);
  int gain_i = mp_obj_get_int(gain);
  // Inference takes ~120 ms of pure C with no Python objects touched, so
  // drop the GIL: a `_thread` running e.g. motor control keeps executing
  // (on the other core when it's free) instead of stalling until we return.
  MP_THREAD_GIL_EXIT();
  int32_t result = kws_predict(bufinfo.buf, bufinfo.len, bias_i, gain_i);
  MP_THREAD_GIL_ENTER();
  return mp_obj_new_int(result);
}

static mp_obj_t export_mfcc(mp_obj_t output) {
  mp_buffer_info_t bufout;
  mp_get_buffer_raise(output, &bufout, MP_BUFFER_WRITE);
  kws_export_mfcc(bufout.buf);
  return mp_obj_new_int(0);
}

static mp_obj_t normalize(mp_obj_t input, mp_obj_t output) {
  mp_buffer_info_t bufin;
  mp_get_buffer_raise(input, &bufin, MP_BUFFER_READ);
  mp_buffer_info_t bufout;
  mp_get_buffer_raise(output, &bufout, MP_BUFFER_WRITE);
  kws_normalize(bufin.buf, bufout.buf);
  return mp_obj_new_int(0);
}

static mp_obj_t normalize_audio(mp_obj_t input, mp_obj_t output,
  mp_obj_t gain) {
  mp_buffer_info_t bufin;
  mp_get_buffer_raise(input, &bufin, MP_BUFFER_READ);
  mp_buffer_info_t bufout;
  mp_get_buffer_raise(output, &bufout, MP_BUFFER_WRITE);
  kws_normalize_audio(bufin.buf, bufout.buf, bufin.len,
    0, mp_obj_get_int(gain));
  return mp_obj_new_int(0);
}

static mp_obj_t compute_mfcc(mp_obj_t input, mp_obj_t output) {
  mp_buffer_info_t bufin;
  mp_get_buffer_raise(input, &bufin, MP_BUFFER_READ);
  mp_buffer_info_t bufout;
  mp_get_buffer_raise(output, &bufout, MP_BUFFER_WRITE);
  kws_compute_mfcc(bufin.buf, bufout.buf);
  return mp_obj_new_int(0);
}

static mp_obj_t predict2(mp_obj_t input) {
  mp_buffer_info_t bufinfo;
  mp_get_buffer_raise(input, &bufinfo, MP_BUFFER_READ);
  return mp_obj_new_int(kws_predict2(bufinfo.buf));
}

static MP_DEFINE_CONST_FUN_OBJ_1(init_obj, init);
static MP_DEFINE_CONST_FUN_OBJ_3(predict_obj, predict);
static MP_DEFINE_CONST_FUN_OBJ_1(export_mfcc_obj, export_mfcc);
static MP_DEFINE_CONST_FUN_OBJ_1(set_debug_obj, set_debug);
static MP_DEFINE_CONST_FUN_OBJ_2(normalize_obj, normalize);
static MP_DEFINE_CONST_FUN_OBJ_3(normalize_audio_obj, normalize_audio);
static MP_DEFINE_CONST_FUN_OBJ_2(compute_mfcc_obj, compute_mfcc);
static MP_DEFINE_CONST_FUN_OBJ_1(predict2_obj, predict2);

static const mp_rom_map_elem_t nnom_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_speech_commands) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&init_obj) },
    { MP_ROM_QSTR(MP_QSTR_predict), MP_ROM_PTR(&predict_obj) },
    { MP_ROM_QSTR(MP_QSTR_export_mfcc), MP_ROM_PTR(&export_mfcc_obj) },
    // { MP_ROM_QSTR(MP_QSTR_set_debug), MP_ROM_PTR(&set_debug_obj) },
    // { MP_ROM_QSTR(MP_QSTR_normalize), MP_ROM_PTR(&normalize_obj) },
    // { MP_ROM_QSTR(MP_QSTR_normalize_audio), MP_ROM_PTR(&normalize_audio_obj) },
    // { MP_ROM_QSTR(MP_QSTR_compute_mfcc), MP_ROM_PTR(&compute_mfcc_obj) },
    // { MP_ROM_QSTR(MP_QSTR_predict2), MP_ROM_PTR(&predict2_obj) },
};

static MP_DEFINE_CONST_DICT(nnom_module_globals, nnom_module_globals_table);

const mp_obj_module_t nnom_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&nnom_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_speech_commands, nnom_module);
