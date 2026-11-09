#ifndef COA_MESSAGE_H
#define COA_MESSAGE_H
#include <stdint.h>
#define SERVER_PORT 5678
#define NODE_PORT 8765
#define FIRST_NODE_ID 2
#define LAST_NODE_ID 9
#define NODE_COUNT 8
#define MSG_REG 1
#define MSG_CONFIG 2
#define MSG_READING 3
#define MSG_AGGREGATE 4
#define MSG_DIRECT 5
/* Fixed wire layout: uint8_t only; avoids native alignment/endianness issues. */
typedef struct {
  uint8_t type;
  uint8_t from;
  uint8_t cluster_head;
  uint8_t epoch;
  uint8_t seq_high;
  uint8_t seq_low;
  uint8_t count_high;
  uint8_t count_low;
  uint8_t ch_ip[16];
} coa_message_t;
static inline uint16_t coa_count(const coa_message_t *f) { return ((uint16_t)f->count_high << 8) | f->count_low; }
static inline void coa_set_count(coa_message_t *f, uint16_t n) {
  f->count_high = (uint8_t)(n >> 8); f->count_low = (uint8_t)(n & 255);
}
#endif
