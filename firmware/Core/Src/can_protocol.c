/**
 * @file    can_protocol.c
 * @brief   CAN application protocol: IDs, payload packing, counter + CRC.
 *          Pure C99, no hardware dependency -> unit tested on the host
 *          (firmware/tests/test_can_protocol.c).
 */
#include "can_protocol.h"

#include <string.h>

uint8_t canp_crc8_j1850(const uint8_t *data, size_t len)
{
    uint8_t crc = 0xFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 0x80u) ? (uint8_t)((crc << 1) ^ 0x1Du) : (uint8_t)(crc << 1);
        }
    }
    return (uint8_t)(crc ^ 0xFFu);
}

uint8_t canp_frame_crc(uint16_t id, const uint8_t d[8])
{
    uint8_t buf[9];
    buf[0] = (uint8_t)(id & 0xFFu);
    buf[1] = (uint8_t)((id >> 8) & 0x07u);
    memcpy(&buf[2], d, 7);
    return canp_crc8_j1850(buf, sizeof buf);
}

void canp_seal(uint16_t id, uint8_t d[8], uint8_t *tx_counter, uint8_t status_nibble)
{
    d[6] = (uint8_t)(((status_nibble & 0x0Fu) << 4) | (*tx_counter & 0x0Fu));
    *tx_counter = (uint8_t)((*tx_counter + 1u) & 0x0Fu);
    d[7] = canp_frame_crc(id, d);
}

uint8_t canp_counter(const uint8_t d[8]) { return (uint8_t)(d[6] & 0x0Fu); }
uint8_t canp_status(const uint8_t d[8])  { return (uint8_t)(d[6] >> 4); }

canp_result_t canp_check(uint16_t id, uint8_t dlc, const uint8_t d[8], canp_rx_state_t *st)
{
    if (dlc != CANP_DLC) {
        st->errors++;
        return CANP_ERR_DLC;
    }
    if (canp_frame_crc(id, d) != d[7]) {
        st->errors++;
        return CANP_ERR_CRC;
    }
    uint8_t c = canp_counter(d);
    canp_result_t r = CANP_OK;
    if (st->valid) {
        uint8_t expected = (uint8_t)((st->last_counter + 1u) & 0x0Fu);
        if (c == st->last_counter) {
            st->errors++;
            return CANP_ERR_COUNTER_REPEAT;
        }
        if (c != expected) {
            st->lost += (uint32_t)((uint8_t)(c - expected) & 0x0Fu);
            r = CANP_OK_COUNTER_JUMP;
        }
    }
    st->valid = true;
    st->last_counter = c;
    return r;
}

uint16_t canp_id(uint8_t node, canp_msg_t msg)
{
    return (uint16_t)(CANP_BASE_ID + ((uint16_t)(node & 0x03u) << 4) + (uint16_t)msg);
}

bool canp_decode_id(uint16_t id, uint8_t *node, canp_msg_t *msg)
{
    if (id < CANP_BASE_ID || id >= CANP_BASE_ID + (CANP_MAX_NODES << 4)) {
        return false;
    }
    uint16_t off = (uint16_t)(id - CANP_BASE_ID);
    if ((off & 0x0Fu) >= (uint16_t)CANP_MSG_COUNT) {
        return false;
    }
    *node = (uint8_t)(off >> 4);
    *msg = (canp_msg_t)(off & 0x0Fu);
    return true;
}

uint16_t canp_cmd_id(uint8_t target)
{
    return (target == 0xFFu) ? (uint16_t)CANP_CMD_BROADCAST_ID : (uint16_t)(CANP_CMD_BASE_ID + (target & 0x03u));
}

bool canp_is_cmd_for(uint16_t id, uint8_t node)
{
    return id == CANP_CMD_BROADCAST_ID || id == canp_cmd_id(node);
}

void canp_put_u16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)(v & 0xFFu);
    p[1] = (uint8_t)(v >> 8);
}

uint16_t canp_get_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

void canp_enc_heartbeat(uint8_t d[8], const canp_heartbeat_t *m)
{
    d[0] = m->node_id;
    d[1] = (uint8_t)m->state;
    canp_put_u16(&d[2], m->faults);
    d[4] = m->peers_alive;
    d[5] = m->fw_version;
}

void canp_dec_heartbeat(const uint8_t d[8], canp_heartbeat_t *m)
{
    m->node_id = d[0];
    m->state = (node_state_t)(d[1] & 0x03u);
    m->faults = canp_get_u16(&d[2]);
    m->peers_alive = d[4];
    m->fw_version = d[5];
}

void canp_enc_vec3(uint8_t d[8], const canp_vec3_t *m)
{
    canp_put_u16(&d[0], (uint16_t)m->x);
    canp_put_u16(&d[2], (uint16_t)m->y);
    canp_put_u16(&d[4], (uint16_t)m->z);
}

void canp_dec_vec3(const uint8_t d[8], canp_vec3_t *m)
{
    m->x = (int16_t)canp_get_u16(&d[0]);
    m->y = (int16_t)canp_get_u16(&d[2]);
    m->z = (int16_t)canp_get_u16(&d[4]);
}

void canp_enc_board(uint8_t d[8], const canp_board_t *m)
{
    canp_put_u16(&d[0], m->vin_mv);
    canp_put_u16(&d[2], (uint16_t)m->imu_temp_cdeg);
    canp_put_u16(&d[4], m->uptime_s);
}

void canp_dec_board(const uint8_t d[8], canp_board_t *m)
{
    m->vin_mv = canp_get_u16(&d[0]);
    m->imu_temp_cdeg = (int16_t)canp_get_u16(&d[2]);
    m->uptime_s = canp_get_u16(&d[4]);
}

void canp_enc_diag(uint8_t d[8], const canp_diag_t *m)
{
    d[0] = m->tec; d[1] = m->rec; d[2] = m->proto_flags;
    d[3] = m->busoff_count; d[4] = m->e2e_errors; d[5] = m->reset_cause;
}

void canp_dec_diag(const uint8_t d[8], canp_diag_t *m)
{
    m->tec = d[0]; m->rec = d[1]; m->proto_flags = d[2];
    m->busoff_count = d[3]; m->e2e_errors = d[4]; m->reset_cause = d[5];
}

void canp_enc_command(uint8_t d[8], const canp_command_t *m)
{
    memset(d, 0, 6);
    d[0] = (uint8_t)m->cmd;
    d[1] = m->source_node;
    d[2] = m->arg;
}

void canp_dec_command(const uint8_t d[8], canp_command_t *m)
{
    m->cmd = (canp_cmd_t)d[0];
    m->source_node = d[1];
    m->arg = d[2];
}

void canp_peer_rx(canp_peer_t *p, uint32_t now_ms, const canp_heartbeat_t *hb)
{
    p->seen = true;
    p->alive = true;
    p->last_rx_ms = now_ms;
    p->state = hb->state;
    p->faults = hb->faults;
}

bool canp_peer_poll(canp_peer_t *p, uint32_t now_ms)
{
    if (p->alive && (uint32_t)(now_ms - p->last_rx_ms) > CANP_HEARTBEAT_TIMEOUT_MS) {
        p->alive = false;
        return true;
    }
    return false;
}
