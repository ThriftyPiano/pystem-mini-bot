// Keyword spotting built on NNoM (https://github.com/majianjia/nnom) by
// Jianjia Ma, Apache-2.0. MFCC front end and model architecture derived from
// NNoM's keyword_spotting example.
#include <math.h>
#include <stdint.h>
#include <string.h>
#include <stdbool.h>
#include "mfcc.h"
#include "nnom.h"
#include "weights.h"

#define AUDIO_FRAME_LEN 512
#define MFCC_NUM_FRAMES 61
#define MFCC_COEFFS_LEN 12
#define MFCC_NUM_BANK	26
#define FEATURE_COUNT 576

int16_t audio_buffer[(int)(AUDIO_FRAME_LEN * 1.5)] = {0};

int debug = 0;
mfcc_t* mfcc = 0;
float mfcc_coeffs[MFCC_COEFFS_LEN] = {0};
int8_t mfcc_buffer[MFCC_NUM_FRAMES][MFCC_COEFFS_LEN] = {0};
int mfcc_buffer_index = 0;

nnom_model_t* model = 0;

void kws_set_debug(int val) {
  debug = val;
}

void kws_normalize(float* input, int8_t* output) {
  for (int i = 0; i < MFCC_COEFFS_LEN; i++) {
    float val = input[i];
    val = val > 13.61 ? 13.61 : val;
    val = val < -16.39 ? -16.39 : val;
    val += 1.39;
    val = val * 127.0 / 15.0;
    output[i] = (int8_t)round(val);
    if (debug) {
      printf("%f:%d,", input[i], output[i]);
    }
  }
  if (debug) {
    printf("MFCC\n");
  }
}

void kws_init(int8_t* buffer) {
  int8_t label_count = buffer[0];
  int8_t weight_dec_bits = buffer[1];
  int8_t bias_dec_bits = buffer[2];
  int8_t bias_shift = buffer[3];
  int8_t output_shift = buffer[4];
  int8_t* weight = buffer + 5;
  int8_t* bias = buffer + 5 + FEATURE_COUNT * (int)label_count;

  if (!mfcc) {
    mfcc = mfcc_create(MFCC_COEFFS_LEN + 1, 1, MFCC_NUM_BANK,
      AUDIO_FRAME_LEN, 0.97f, true);
  }

  static nnom_shape_data_t weight_dim[] = {FEATURE_COUNT, 0};
  weight_dim[1] = label_count;
  static nnom_qformat_param_t weight_dec = 0;
  weight_dec = weight_dec_bits;
  static nnom_tensor_t weight_tensor = {0};
  nnom_tensor_t t = {
    .p_data = (void*)weight,
    .dim = (nnom_shape_data_t*)weight_dim,
    .q_dec = (nnom_qformat_param_t*)&weight_dec,
    .q_offset = (nnom_qformat_param_t*)tensor_dense_kernel_0_offset,
    .qtype = NNOM_QTYPE_PER_TENSOR,
    .num_dim = 2,
    .bitwidth = 8
  };
  weight_tensor = t;

  static nnom_shape_data_t bias_dim[] = {0};
  bias_dim[0] = label_count;
  static nnom_qformat_param_t bias_dec = 0;
  bias_dec = bias_dec_bits;
  static nnom_tensor_t bias_tensor = {0};
  nnom_tensor_t t2 = {
    .p_data = (void*)bias,
    .dim = (nnom_shape_data_t*)bias_dim,
    .q_dec = (nnom_qformat_param_t*)&bias_dec,
    .q_offset = (nnom_qformat_param_t*)tensor_dense_bias_0_offset,
    .qtype = NNOM_QTYPE_PER_TENSOR,
    .num_dim = 1,
    .bitwidth = 8
  };
  bias_tensor = t2;

  static nnom_qformat_param_t dense_output_shift[] = DENSE_OUTPUT_RSHIFT;
  dense_output_shift[0] = output_shift;
  static nnom_qformat_param_t dense_bias_shift[] = DENSE_BIAS_LSHIFT;
  dense_bias_shift[0] = bias_shift;
  static nnom_dense_config_t dense_config = {0};
  nnom_dense_config_t c = {
    .super = {.name = "dense_3"},
    .qtype = NNOM_QTYPE_PER_TENSOR,
    .weight = (nnom_tensor_t*)&weight_tensor,
    .bias = (nnom_tensor_t*)&bias_tensor,
    .output_shift = (nnom_qformat_param_t *)&dense_output_shift,
    .bias_shift = (nnom_qformat_param_t *)&dense_bias_shift
  };
  dense_config = c;

  static nnom_shape_data_t output_dim = 0;
  output_dim = label_count;
  static nnom_tensor_t output_tensor = {0};
  nnom_tensor_t t3 = {
    .p_data = (void*)nnom_output_data,
    .dim = (nnom_shape_data_t*)&output_dim,
    .q_dec = (nnom_qformat_param_t*)tensor_output0_dec,
    .q_offset = (nnom_qformat_param_t*)tensor_output0_offset,
    .qtype = NNOM_QTYPE_PER_TENSOR,
    .num_dim = 1,
    .bitwidth = 8
  };
  output_tensor = t3;
  static nnom_io_config_t output_config = {0};
  nnom_io_config_t c2 = {
    .super = {.name = "output0"},
    .tensor = (nnom_tensor_t*)&output_tensor
  };
  output_config = c2;

	check_model_version(NNOM_MODEL_VERSION);
  if (model) {
    model_delete(model);
  }
	model = new_model(0);

	nnom_layer_t* layer[15];
	layer[0] = input_s(&input_1_config);
	layer[1] = model->hook(conv2d_s(&conv2d_config), layer[0]);
	layer[2] = model->active(act_relu(), layer[1]);
	layer[3] = model->hook(maxpool_s(&max_pooling2d_config), layer[2]);
	layer[4] = model->hook(conv2d_s(&conv2d_1_config), layer[3]);
	layer[5] = model->active(act_relu(), layer[4]);
	layer[6] = model->hook(maxpool_s(&max_pooling2d_1_config), layer[5]);
	layer[7] = model->hook(conv2d_s(&conv2d_2_config), layer[6]);
	layer[8] = model->active(act_relu(), layer[7]);
	layer[9] = model->hook(conv2d_s(&conv2d_3_config), layer[8]);
	layer[10] = model->active(act_relu(), layer[9]);
	layer[11] = model->hook(flatten_s(&flatten_config), layer[10]);
	layer[12] = model->hook(dense_s(&dense_config), layer[11]);
	layer[13] = model->hook(softmax_s(&softmax_config), layer[12]);
	layer[14] = model->hook(output_s(&output_config), layer[13]);
	model_compile(model, layer[0], layer[14]);
}

void kws_normalize_audio(int16_t* input, int16_t* output, int len,
  int bias, int gain) {
  if (bias == 0 && gain <= 1) {
    return;
  }
  for (int i = 0; i < len; i++) {
    int32_t n = input[i];
    n = (n + bias) * gain;
    n = n > 32767 ? 32767 : n;
    n = n < -32767 ? -32767 : n;
    output[i] = (int16_t)n;
  }
}

void kws_append_to_mfcc_buffer(int16_t* audio_frame, int bias, int gain) {
  for (int i = 0; i < AUDIO_FRAME_LEN; i++) {
    audio_buffer[AUDIO_FRAME_LEN / 2 + i] = audio_frame[i];
    if (debug) {
      printf("%d,", audio_frame[i]);
    }
  }
  if (debug) {
    printf("AUDIO\n");
  }
  kws_normalize_audio(&audio_buffer[AUDIO_FRAME_LEN / 2],
    &audio_buffer[AUDIO_FRAME_LEN / 2], AUDIO_FRAME_LEN, bias, gain);
  for (int i = 0; i < 2; i++) {
    mfcc_compute(mfcc, &audio_buffer[i * AUDIO_FRAME_LEN / 2], mfcc_coeffs);
    kws_normalize(mfcc_coeffs, mfcc_buffer[mfcc_buffer_index]);
    mfcc_buffer_index = ++mfcc_buffer_index % MFCC_NUM_FRAMES;
  }
  for (int i = 0; i < AUDIO_FRAME_LEN / 2; i++) {
    audio_buffer[i] = audio_frame[AUDIO_FRAME_LEN / 2 + i];
  }
  kws_normalize_audio(&audio_buffer[0],
    &audio_buffer[0], AUDIO_FRAME_LEN / 2, bias, gain);
}

void kws_compute_mfcc(int16_t* audio_frame, float* mfcc_output) {
  mfcc_compute(mfcc, audio_frame, mfcc_output);
}

int32_t kws_predict2(int8_t* input) {
  memcpy(&nnom_input_data[0], input, MFCC_NUM_FRAMES * MFCC_COEFFS_LEN);
  uint32_t label;
  float prob;
  nnom_predict(model, &label, &prob);
  return label * 1000 + (int)round(prob * 100);
}

int32_t kws_predict(int16_t* audio_input, int num_bytes, int bias, int gain) {
  int num_frames = num_bytes / (2 * AUDIO_FRAME_LEN);
  for (int i = 0; i < num_frames; i++) {
    kws_append_to_mfcc_buffer(&audio_input[i * AUDIO_FRAME_LEN], bias, gain);
  }
  int first_part_len = (MFCC_NUM_FRAMES - mfcc_buffer_index) * MFCC_COEFFS_LEN;
  int second_part_len = mfcc_buffer_index * MFCC_COEFFS_LEN;
  memcpy(&nnom_input_data[0], &mfcc_buffer[mfcc_buffer_index], first_part_len);
  memcpy(&nnom_input_data[first_part_len], mfcc_buffer, second_part_len);
  if (debug) {
    for (int i = 0; i < MFCC_NUM_FRAMES; i++) {
      printf("%d:", i);
      for (int j = 0; j < MFCC_COEFFS_LEN; j++) {
        printf("%d,", nnom_input_data[i * MFCC_COEFFS_LEN + j]);
      }
    }
    printf("FEAT\n");
  }
  uint32_t label;
  float prob;
  nnom_predict(model, &label, &prob);
  if (debug) {
    printf("%d,%f,LABEL\n", label, prob);
  }
  return label * 1000 + (int)round(prob * 100);
}

void kws_export_mfcc(int8_t* buffer) {
  memcpy(buffer, &nnom_input_data[0], MFCC_NUM_FRAMES * MFCC_COEFFS_LEN);
}
