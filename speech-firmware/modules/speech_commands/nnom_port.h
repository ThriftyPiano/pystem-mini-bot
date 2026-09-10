#include "py/runtime.h"
#define nnom_malloc(n)       m_malloc(n)
#define nnom_free(ptr)       m_free(ptr)
#define nnom_memset(s, c, n) memset(s, c, n)
#define nnom_memcpy(d, s, n) memmove(d, s, n)
#define nnom_us_get()        0
#define nnom_ms_get()        0
#define NNOM_LOG(...)        printf(__VA_ARGS__)
#define NNOM_BLOCK_NUM       (8)
#define DENSE_WEIGHT_OPT     (1)
