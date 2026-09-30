/**
 * @file    can_protocol.h
 * @brief   CAN application protocol of the STM32 CAN ECU (pure C, no HAL).
 *
 * All frames: classic CAN, 11-bit IDs, DLC 8, little-endian (Intel) signals.
 *   byte 6 : bits 0..3 rolling counter (0..15), bits 4..7 status nibble
 *   byte 7 : CRC-8 SAE J1850 (poly 0x1D, init 0xFF, xorout 0xFF) computed over
 *            [ID low byte, ID high byte, byte0 .. byte6]
 * The counter/CRC scheme is *inspired by* AUTOSAR E2E profiles; it is NOT an
 * implementation of, and makes no claim of compliance with, any AUTOSAR profile
 * or ISO 26262.  Full definition: docs/CAN_PROTOCOL.md and tools/can_ecu.dbc.
 */
#ifndef CAN_PROTOCOL_H
#define CAN_PROTOCOL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CANP_BASE_ID            0x100u  /* 0x100 + (node << 4) + msg          */
#define CANP_CMD_BASE_ID        0x0F0u  /* 0x0F0 + target node                */
#define CANP_CMD_BROADCAST_ID   0x0FFu  /* command to all nodes                */
#define CANP_MAX_NODES          4u      /* node id from 2 solder jumpers       */
#define CANP_DLC                8u
#define CANP_FW_VERSION         0x10u   /* major.minor as nibbles -> 1.0       */

/* transmit periods and supervision */
#define CANP_PERIOD_HEARTBEAT_MS  100u
#define CANP_PERIOD_ACCEL_MS       20u
#define CANP_PERIOD_GYRO_MS        20u
#define CANP_PERIOD_BOARD_MS      100u
#define CANP_PERIOD_DIAG_MS      1000u
#define CANP_HEARTBEAT_TIMEOUT_MS 300u  /* 3 missed heartbeats                 */

typedef enum {
    CANP_MSG_HEARTBEAT = 0,
    CANP_MSG_ACCEL     = 1,
    CANP_MSG_GYRO      = 2,
    CANP_MSG_BOARD     = 3,
    CANP_MSG_DIAG      = 4,
    CANP_MSG_COUNT
} canp_msg_t;

typedef enum {
    NODE_STATE_INIT     = 0,
    NODE_STATE_RUN      = 1,
    NODE_STATE_DEGRADED = 2,
    NODE_STATE_FAULT    = 3
} node_state_t;

typedef enum {
    CANP_CMD_NONE         = 0,
    CANP_CMD_IDENTIFY     = 1,  /* blink STATUS LED fast for 3 s           */
    CANP_CMD_CLEAR_FAULTS = 2   /* clear latched fault history             */
} canp_cmd_t;

typedef enum {
    CANP_OK = 0,
    CANP_OK_COUNTER_JUMP,       /* valid frame, but frames were lost        */
    CANP_ERR_DLC,
    CANP_ERR_CRC,
    CANP_ERR_COUNTER_REPEAT     /* same counter as previous frame (stale)   */
} canp_result_t;

/* status nibble (byte 6 bits 4..7) */
#define CANP_ST_DATA_VALID    0x1u
#define CANP_ST_SENSOR_FAULT  0x2u
#define CANP_ST_DEGRADED      0x4u
#define CANP_ST_RESERVED      0x8u

/* diag protocol flags (diag byte 2) */
#define CANP_PF_WARNING       0x01u
#define CANP_PF_PASSIVE       0x02u
#define CANP_PF_BUSOFF        0x04u
#define CANP_PF_LEC_SHIFT     3u      /* bits 3..5 last error code */
#define CANP_PF_LEC_MASK      0x38u

typedef struct {
    uint8_t      node_id;
    node_state_t state;
    uint16_t     faults;       /* FAULT_* bit field, see diagnostics.h */
    uint8_t      peers_alive;  /* bit n = node n heartbeat received in time */
    uint8_t      fw_version;
} canp_heartbeat_t;

typedef struct { int16_t x, y, z; } canp_vec3_t; /* accel: mg, gyro: 0.1 dps */

typedef struct {
    uint16_t vin_mv;
    int16_t  imu_temp_cdeg;    /* 0.01 degC */
    uint16_t uptime_s;         /* wraps after 18.2 h */
} canp_board_t;

typedef struct {
    uint8_t tec, rec, proto_flags, busoff_count, e2e_errors, reset_cause;
} canp_diag_t;

typedef struct {
    canp_cmd_t cmd;
    uint8_t    source_node;
    uint8_t    arg;
} canp_command_t;

typedef struct {
    bool     valid;            /* at least one frame accepted */
    uint8_t  last_counter;
    uint32_t lost;             /* frames missed (counter jumps) */
    uint32_t errors;           /* CRC / DLC / repeated counter */
} canp_rx_state_t;

typedef struct {
    bool         seen;         /* at least one heartbeat ever received */
    bool         alive;
    uint32_t     last_rx_ms;
    node_state_t state;
    uint16_t     faults;
} canp_peer_t;

/* --- integrity ---------------------------------------------------------- */
uint8_t canp_crc8_j1850(const uint8_t *data, size_t len);
uint8_t canp_frame_crc(uint16_t id, const uint8_t d[8]);
void    canp_seal(uint16_t id, uint8_t d[8], uint8_t *tx_counter, uint8_t status_nibble);
canp_result_t canp_check(uint16_t id, uint8_t dlc, const uint8_t d[8], canp_rx_state_t *st);
uint8_t canp_counter(const uint8_t d[8]);
uint8_t canp_status(const uint8_t d[8]);

/* --- identifiers -------------------------------------------------------- */
uint16_t canp_id(uint8_t node, canp_msg_t msg);
bool     canp_decode_id(uint16_t id, uint8_t *node, canp_msg_t *msg);
uint16_t canp_cmd_id(uint8_t target);      /* target 0xFF -> broadcast */
bool     canp_is_cmd_for(uint16_t id, uint8_t node);

/* --- byte helpers (little endian) --------------------------------------- */
void     canp_put_u16(uint8_t *p, uint16_t v);
uint16_t canp_get_u16(const uint8_t *p);

/* --- payload encode / decode (bytes 0..5; seal adds 6 and 7) ------------ */
void canp_enc_heartbeat(uint8_t d[8], const canp_heartbeat_t *m);
void canp_dec_heartbeat(const uint8_t d[8], canp_heartbeat_t *m);
void canp_enc_vec3(uint8_t d[8], const canp_vec3_t *m);
void canp_dec_vec3(const uint8_t d[8], canp_vec3_t *m);
void canp_enc_board(uint8_t d[8], const canp_board_t *m);
void canp_dec_board(const uint8_t d[8], canp_board_t *m);
void canp_enc_diag(uint8_t d[8], const canp_diag_t *m);
void canp_dec_diag(const uint8_t d[8], canp_diag_t *m);
void canp_enc_command(uint8_t d[8], const canp_command_t *m);
void canp_dec_command(const uint8_t d[8], canp_command_t *m);

/* --- peer supervision --------------------------------------------------- */
void canp_peer_rx(canp_peer_t *p, uint32_t now_ms, const canp_heartbeat_t *hb);
/** @return true exactly once, when the peer transitions alive -> timed out */
bool canp_peer_poll(canp_peer_t *p, uint32_t now_ms);

#ifdef __cplusplus
}
#endif
#endif /* CAN_PROTOCOL_H */
