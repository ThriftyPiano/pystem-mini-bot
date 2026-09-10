#include "py/runtime.h"
#include "esp_heap_caps.h"
// Internal SRAM only: on SPIRAM builds the MicroPython heap lives in (much
// slower) PSRAM, which roughly doubles inference time if NNoM's working
// buffers land there.
#define nnom_malloc(n)       heap_caps_malloc(n, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT)
#define nnom_free(ptr)       heap_caps_free(ptr)
#define nnom_memset(s, c, n) memset(s, c, n)
#define nnom_memcpy(d, s, n) memmove(d, s, n)
#define nnom_us_get()        0
#define nnom_ms_get()        0
#define NNOM_LOG(...)        printf(__VA_ARGS__)
#define NNOM_BLOCK_NUM       (8)
#define DENSE_WEIGHT_OPT     (1)
