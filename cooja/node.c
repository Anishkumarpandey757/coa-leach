/* Contiki-NG simulated sensor: application-layer cluster-head aggregation.
 * All traffic uses RPL/IPv6/UDP. Packet forwarding can physically traverse
 * the RPL root even for member -> CH (RPL non-storing source routes).
 */
#include "contiki.h"
#include "net/routing/routing.h"
#include "net/netstack.h"
#include "net/ipv6/simple-udp.h"
#include "sys/energest.h"
#include "sys/log.h"
#include "node-id.h"
#include "message.h"
#include <string.h>
#include <stdio.h>
#include <stdint.h>

#define REPORT_INTERVAL (15 * CLOCK_SECOND)
#define LOG_INTERVAL 4
#define LOG_MODULE "COA-NODE"
#define LOG_LEVEL LOG_LEVEL_INFO

static struct simple_udp_connection conn;
static uip_ipaddr_t ch_addr;
static uint8_t head = 0, epoch = 0, has_ch_addr = 0;
static uint16_t sequence, pending, received_packets, sent_packets;
PROCESS(coa_node_process, "COA-APSO-LEACH sensor");
AUTOSTART_PROCESSES(&coa_node_process);

static void on_packet(struct simple_udp_connection *conn_ptr,
    const uip_ipaddr_t *sender, uint16_t sender_port,
    const uip_ipaddr_t *receiver, uint16_t receiver_port,
    const uint8_t *data, uint16_t length)
{
  coa_message_t m;
  static const uint8_t zero_ip[16] = {0};
  if(length != sizeof(m)) return;
  memcpy(&m, data, sizeof(m));
  if(m.type == MSG_CONFIG) {
    head = m.cluster_head;
    epoch = m.epoch;
    has_ch_addr = memcmp(m.ch_ip, zero_ip, 16) != 0;
    if(has_ch_addr) memcpy(ch_addr.u8, m.ch_ip, 16);
    LOG_INFO("CONFIG id=%u CH=%u epoch=%u role=%s CHIP=%s\n",
      node_id, head, epoch, (node_id == head) ? "HEAD" : "MEMBER",
      has_ch_addr ? "available" : "pending");
  } else if(m.type == MSG_READING && node_id == head && m.cluster_head == node_id) {
    pending += coa_count(&m);
    received_packets++;
    LOG_INFO("CLUSTER RX from=%u aggregate_pending=%u\n",m.from,pending);
  }
}

static void send_message(uint8_t kind, uint8_t count, const uip_ipaddr_t *dest)
{
  coa_message_t f;
  memset(&f, 0, sizeof(f));
  f.type=kind;
  f.from=(uint8_t)node_id;
  f.cluster_head=head;
  f.epoch=epoch;
  f.seq_high=(uint8_t)(sequence>>8);
  f.seq_low=(uint8_t)(sequence & 255);
  coa_set_count(&f, count);
  simple_udp_sendto_port(&conn, &f, sizeof(f), dest,
    kind == MSG_READING ? NODE_PORT : SERVER_PORT);
  sent_packets++;
}

PROCESS_THREAD(coa_node_process, ev, data)
{
  static struct etimer periodic;
  static uip_ipaddr_t root;
  PROCESS_BEGIN();
  simple_udp_register(&conn, NODE_PORT, NULL, 0, on_packet);
  etimer_set(&periodic, (5 + (node_id % 8)) * CLOCK_SECOND);
  while(1) {
    PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&periodic));
    if(NETSTACK_ROUTING.node_is_reachable() && NETSTACK_ROUTING.get_root_ipaddr(&root)) {
      /* Registers location and energy-report opportunity, with root response. */
      send_message(MSG_REG, 0, &root);
      if(head == node_id) {
        /* Cluster head aggregates its own value plus received member values. */
        pending++;
        send_message(MSG_AGGREGATE, (uint8_t)(pending > 255 ? 255 : pending), &root);
        LOG_INFO("HEAD FLUSH n=%u epoch=%u\n",pending,epoch);
        pending = 0;
      } else if(has_ch_addr && head >= FIRST_NODE_ID && head <= LAST_NODE_ID) {
        send_message(MSG_READING, 1, &ch_addr);
        LOG_INFO("MEMBER DATA %u -> head=%u\n",node_id,head);
      } else {
        send_message(MSG_DIRECT, 1, &root);
        LOG_INFO("MEMBER FALLBACK %u -> root\n",node_id);
      }
      if(sequence % LOG_INTERVAL == 0) {
        energest_flush();
        LOG_INFO("ENERGEST id=%u tx_ticks=%lu rx_ticks=%lu cpu_ticks=%lu\n",
          node_id, (unsigned long)energest_type_time(ENERGEST_TYPE_TRANSMIT),
          (unsigned long)energest_type_time(ENERGEST_TYPE_LISTEN),
          (unsigned long)energest_type_time(ENERGEST_TYPE_CPU));
      }
      sequence++;
    } else {
      LOG_INFO("NO ROUTE id=%u\n",node_id);
    }
    etimer_set(&periodic, REPORT_INTERVAL);
  }
  PROCESS_END();
}
