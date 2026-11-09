/* COA-APSO-LEACH Cooja demonstrator: policy-replay DAG root.
 * Cluster assignments come from Python-generated policy.h. The root does NOT
 * run PSO inside the mote or react to radio-measured energy in real time.
 */
#include "contiki.h"
#include "net/routing/routing.h"
#include "net/netstack.h"
#include "net/ipv6/simple-udp.h"
#include "sys/log.h"
#include "message.h"
#include "policy.h"
#include <string.h>
#include <stdio.h>

#define LOG_MODULE "COA-ROOT"
#define LOG_LEVEL LOG_LEVEL_INFO
#define EPOCH_SECONDS 90
#ifndef COA_POLICY_NAME
#define COA_POLICY_NAME "unnamed"
#endif

static struct simple_udp_connection conn;
static uip_ipaddr_t clients[NODE_COUNT];
static uint8_t registered[NODE_COUNT];
static uint8_t last_assignment[NODE_COUNT];
static uint8_t last_ip_ready[NODE_COUNT];
static uint8_t epoch;
static uint32_t register_count, aggregate_count, received_samples, config_sent;

PROCESS(coa_root_process, "COA AP SO LEACH root");
AUTOSTART_PROCESSES(&coa_root_process);

static void reply_policy(uint8_t id, const uip_ipaddr_t *address)
{
  int index = id - FIRST_NODE_ID;
  uint8_t selected;
  int ch_index;
  coa_message_t response;
  uint8_t ip_ready;
  if(index < 0 || index >= NODE_COUNT) return;
  selected = COA_ASSIGNMENT[epoch % COA_EPOCHS][index];
  ch_index = selected - FIRST_NODE_ID;
  ip_ready = (ch_index >= 0 && ch_index < NODE_COUNT && registered[ch_index]);
  /* Avoid repeated assignment messages when the cluster is unchanged. */
  if(last_assignment[index] == selected && last_ip_ready[index] == ip_ready) return;
  last_assignment[index] = selected;
  last_ip_ready[index] = ip_ready;
  memset(&response, 0, sizeof(response));
  response.type = MSG_CONFIG;
  response.from = 1;
  response.cluster_head = selected;
  response.epoch = epoch;
  if(ch_index >= 0 && ch_index < NODE_COUNT && registered[ch_index]) {
    memcpy(response.ch_ip, clients[ch_index].u8, 16);
  }
  simple_udp_sendto(&conn, &response, sizeof(response), address);
  config_sent++;
  LOG_INFO("ASSIGN node=%u head=%u epoch=%u registeredCH=%u\n", id, selected, epoch,
           ch_index >= 0 && ch_index < NODE_COUNT ? registered[ch_index] : 0);
}

static void on_packet(struct simple_udp_connection *c,
  const uip_ipaddr_t *sender, uint16_t sender_port,
  const uip_ipaddr_t *receiver, uint16_t receiver_port,
  const uint8_t *data, uint16_t length)
{
  coa_message_t message;
  int index;
  if(length != sizeof(message)) return;
  memcpy(&message, data, sizeof(message));
  if(message.from < FIRST_NODE_ID || message.from > LAST_NODE_ID) return;
  index = message.from - FIRST_NODE_ID;
  if(message.type == MSG_REG) {
    uip_ipaddr_copy(&clients[index], sender);
    registered[index] = 1;
    register_count++;
    /* The node reports the head it is using; a mismatch means its CONFIG was lost. */
    if(message.cluster_head != COA_ASSIGNMENT[epoch % COA_EPOCHS][index]) {
      last_assignment[index] = 0;
    }
    reply_policy(message.from, sender);
  } else if(message.type == MSG_AGGREGATE) {
    aggregate_count++;
    received_samples += coa_count(&message);
    LOG_INFO("AGG head=%u epoch=%u samples=%u total=%lu\n", message.from,
       message.epoch, coa_count(&message), (unsigned long)received_samples);
  } else if(message.type == MSG_DIRECT) {
    received_samples += coa_count(&message);
    LOG_INFO("DIRECT node=%u fallback; samples_total=%lu\n",message.from,
      (unsigned long)received_samples);
  }
}

PROCESS_THREAD(coa_root_process, ev, data)
{
  static struct etimer epoch_timer;
  int i;
  PROCESS_BEGIN();
  memset(registered, 0, sizeof(registered));
  memset(last_assignment, 0, sizeof(last_assignment));
  memset(last_ip_ready, 0, sizeof(last_ip_ready));
  NETSTACK_ROUTING.root_start();
  simple_udp_register(&conn, SERVER_PORT, NULL, NODE_PORT, on_packet);
  LOG_INFO("ROOT ready, %u nodes; policy=%s epochs=%u\n", NODE_COUNT, COA_POLICY_NAME, COA_EPOCHS);
  etimer_set(&epoch_timer, EPOCH_SECONDS * CLOCK_SECOND);
  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&epoch_timer));
    epoch = (epoch + 1) % COA_EPOCHS;
    LOG_INFO("NEW EPOCH=%u regs=%lu cfg=%lu agg=%lu samples=%lu\n", epoch,
      (unsigned long)register_count,(unsigned long)config_sent,
      (unsigned long)aggregate_count,(unsigned long)received_samples);
    /* Refresh assignments on the next REG packet from each node. */
    for(i = 0; i < NODE_COUNT; i++) {
      if(registered[i]) reply_policy(i + FIRST_NODE_ID, &clients[i]);
    }
    etimer_reset(&epoch_timer);
  }
  PROCESS_END();
}
