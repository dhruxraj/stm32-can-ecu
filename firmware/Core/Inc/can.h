/**
 * @file    can.h
 * @brief   FDCAN1 driver: classic CAN 500 kbit/s, filters, interrupt RX into a
 *          ring buffer, TX via FIFO queue, bus-off recovery, error counters.
 */
#ifndef CAN_H
#define CAN_H

#include <stdbool.h>
#include <stdint.h>

#define CAN_RX_QUEUE_LEN   32u      /* power of two */
#define CAN_BUSOFF_WAIT_MS 100u     /* wait before requesting bus-off recovery */

typedef struct {
    uint16_t id;
    uint8_t  dlc;
    uint8_t  data[8];
    uint32_t ts_ms;
} can_frame_t;

typedef struct {
    uint8_t  tec;
    uint8_t  rec;
    bool     warning;
    bool     passive;
    bool     busoff;
    uint8_t  lec;              /* last error code 0..7 */
    uint32_t busoff_events;
    uint32_t tx_ok;
    uint32_t tx_fail;
    uint32_t rx_ok;
    uint32_t rx_overflow;
} can_status_t;

bool can_init(uint8_t node_id);
bool can_send(uint16_t id, const uint8_t data[8]);
bool can_receive(can_frame_t *f);
void can_poll(uint32_t now_ms);           /* call from main loop: status + bus-off recovery */
void can_get_status(can_status_t *s);

#endif /* CAN_H */
