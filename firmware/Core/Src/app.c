/**
 * @file    app.c
 * @brief   Application layer of the STM32 CAN ECU.
 *
 * Cooperative scheduler on the 1 ms HAL tick (no RTOS):
 *   10 ms  : CAN RX processing, fault/state update, LEDs, button
 *   20 ms  : IMU read, ACCEL + GYRO frames
 *   100 ms : HEARTBEAT + BOARD frames, VIN measurement, peer supervision
 *   1000 ms: DIAG frame, MCU temperature, UART status line
 * Every task is non-blocking (HAL timeouts <= 20 ms), so the main loop - and
 * therefore the watchdog refresh - keeps running even with sensor or bus faults.
 */
#include "app.h"

#include <stdio.h>
#include <string.h>

#include "board.h"
#include "can.h"
#include "can_protocol.h"
#include "imu.h"
#include "main.h"

typedef struct {
    uint32_t period_ms;
    uint32_t next_ms;
    void (*fn)(uint32_t now);
} task_t;

static uint8_t          s_node;
static diag_t           s_diag;
static bool             s_init_done;
static canp_peer_t      s_peer[CANP_MAX_NODES];
static canp_rx_state_t  s_rx[CANP_MAX_NODES][CANP_MSG_COUNT];
static canp_rx_state_t  s_cmd_rx[CANP_MAX_NODES];
static uint8_t          s_tx_cnt[CANP_MSG_COUNT];
static uint8_t          s_cmd_cnt;
static uint16_t         s_vin_mv;
static int16_t          s_mcu_temp;
static uint32_t         s_identify_until;
static uint32_t         s_led_tx_until, s_led_rx_until;
static uint32_t         s_btn_down_ms;
static bool             s_btn_prev, s_btn_long_done;
static uint32_t         s_last_10ms_run;
static canp_vec3_t      s_peer_accel[CANP_MAX_NODES];
static uint32_t         s_busoff_seen;

/* -------------------------------------------------------------- CAN TX */
static void tx(canp_msg_t msg, uint8_t d[8], uint8_t status, uint32_t now)
{
    uint16_t id = canp_id(s_node, msg);
    canp_seal(id, d, &s_tx_cnt[msg], status);
    if (can_send(id, d)) {
        s_led_tx_until = now + 20u;
    } else {
        diag_note_tx_overflow(&s_diag, now);
    }
}

static void send_command(uint8_t target, canp_cmd_t cmd, uint32_t now)
{
    uint8_t d[8];
    canp_command_t c = { .cmd = cmd, .source_node = s_node, .arg = 0 };
    uint16_t id = canp_cmd_id(target);
    canp_enc_command(d, &c);
    canp_seal(id, d, &s_cmd_cnt, 0);
    if (can_send(id, d)) {
        s_led_tx_until = now + 20u;
    }
}

static uint8_t peers_alive_mask(void)
{
    uint8_t m = 0;
    for (uint8_t n = 0; n < CANP_MAX_NODES; n++) {
        if (s_peer[n].alive) m |= (uint8_t)(1u << n);
    }
    return m;
}

/* -------------------------------------------------------------- CAN RX */
static void handle_frame(const can_frame_t *f, uint32_t now)
{
    s_led_rx_until = now + 20u;
    if (canp_is_cmd_for(f->id, s_node)) {
        canp_command_t c;
        canp_dec_command(f->data, &c);
        canp_result_t r = canp_check(f->id, f->dlc, f->data, &s_cmd_rx[c.source_node & 3u]);
        if (r == CANP_ERR_DLC || r == CANP_ERR_CRC || r == CANP_ERR_COUNTER_REPEAT) {
            diag_note_e2e_error(&s_diag, now);
            return;
        }
        if (c.cmd == CANP_CMD_IDENTIFY) {
            s_identify_until = now + 3000u;
            printf("[cmd] IDENTIFY from node %u\r\n", c.source_node);
        } else if (c.cmd == CANP_CMD_CLEAR_FAULTS) {
            diag_clear_latched(&s_diag);
            printf("[cmd] CLEAR_FAULTS from node %u\r\n", c.source_node);
        }
        return;
    }
    uint8_t node;
    canp_msg_t msg;
    if (!canp_decode_id(f->id, &node, &msg)) {
        return;
    }
    if (node == s_node) {
        /* we never receive our own frames -> another node uses our ID */
        diag_set(&s_diag, FAULT_ID_CONFLICT, true);
        return;
    }
    canp_result_t r = canp_check(f->id, f->dlc, f->data, &s_rx[node][msg]);
    if (r == CANP_ERR_DLC || r == CANP_ERR_CRC || r == CANP_ERR_COUNTER_REPEAT) {
        diag_note_e2e_error(&s_diag, now);
        return;
    }
    switch (msg) {
    case CANP_MSG_HEARTBEAT: {
        canp_heartbeat_t hb;
        canp_dec_heartbeat(f->data, &hb);
        if (!s_peer[node].seen) {
            printf("[can] peer node %u online (fw %u.%u)\r\n", node, hb.fw_version >> 4, hb.fw_version & 15u);
        }
        canp_peer_rx(&s_peer[node], now, &hb);
        break;
    }
    case CANP_MSG_ACCEL:
        canp_dec_vec3(f->data, &s_peer_accel[node]);
        break;
    default:
        break;
    }
}

/* -------------------------------------------------------------- LEDs */
static bool blink(uint32_t now, uint32_t period, uint32_t on_ms)
{
    return (now % period) < on_ms;
}

static void leds(uint32_t now)
{
    bool st;
    if ((int32_t)(s_identify_until - now) > 0) {
        st = blink(now, 100u, 50u);
    } else {
        switch (s_diag.state) {
        case NODE_STATE_INIT:     st = blink(now, 200u, 100u); break;
        case NODE_STATE_RUN:      st = blink(now, 1000u, 100u); break;
        case NODE_STATE_DEGRADED: st = blink(now, 500u, 250u); break;
        default:                  st = false; break;
        }
    }
    board_led(LED_STATUS, st);
    board_led(LED_FAULT, s_diag.active ? true : (s_diag.latched ? blink(now, 2000u, 100u) : false));
    board_led(LED_CANTX, (int32_t)(s_led_tx_until - now) > 0);
    board_led(LED_CANRX, (int32_t)(s_led_rx_until - now) > 0);
}

/* -------------------------------------------------------------- button */
static void button(uint32_t now)
{
    /* 10 ms sampling + 100 nF / 10k RC = debounce */
    bool down = board_button_pressed();
    if (down && !s_btn_prev) {
        s_btn_down_ms = now;
        s_btn_long_done = false;
    }
    if (down && !s_btn_long_done && (uint32_t)(now - s_btn_down_ms) >= 2000u) {
        s_btn_long_done = true;
        diag_clear_latched(&s_diag);
        send_command(0xFFu, CANP_CMD_CLEAR_FAULTS, now);
        printf("[btn] long press: faults cleared (local + broadcast)\r\n");
    }
    if (!down && s_btn_prev && !s_btn_long_done && (uint32_t)(now - s_btn_down_ms) >= 30u) {
        send_command(0xFFu, CANP_CMD_IDENTIFY, now);
        printf("[btn] IDENTIFY sent to all nodes\r\n");
    }
    s_btn_prev = down;
}

/* -------------------------------------------------------------- tasks */
static void task_10ms(uint32_t now)
{
    can_frame_t f;
    int budget = 16;
    while (budget-- > 0 && can_receive(&f)) {
        handle_frame(&f, now);
    }
    can_poll(now);
    can_status_t cs;
    can_get_status(&cs);
    diag_set(&s_diag, FAULT_CAN_BUSOFF, cs.busoff);
    diag_set(&s_diag, FAULT_CAN_PASSIVE, cs.passive);
    while (s_busoff_seen < cs.busoff_events) {
        s_busoff_seen++;
        diag_note_busoff(&s_diag);
        printf("[can] BUS-OFF #%lu, recovery requested\r\n", (unsigned long)s_busoff_seen);
    }
    diag_set(&s_diag, FAULT_IMU_COMM, g_imu.status == IMU_ST_COMM_FAULT || g_imu.status == IMU_ST_UNINIT);
    diag_set(&s_diag, FAULT_IMU_DATA, g_imu.status == IMU_ST_DATA_FAULT);
    (void)diag_update(&s_diag, now, s_init_done);
    button(now);
    leds(now);
    s_last_10ms_run = now;
}

static void task_20ms(uint32_t now)
{
    imu_service(&g_imu, now);
    if (s_diag.state == NODE_STATE_INIT) {
        return;
    }
    uint8_t st = (uint8_t)((g_imu.valid ? CANP_ST_DATA_VALID : 0u) |
                           (g_imu.status != IMU_ST_OK ? CANP_ST_SENSOR_FAULT : 0u));
    uint8_t d[8];
    canp_vec3_t v = { g_imu.sample.ax_mg, g_imu.sample.ay_mg, g_imu.sample.az_mg };
    canp_enc_vec3(d, &v);
    tx(CANP_MSG_ACCEL, d, st, now);
    canp_vec3_t g = { g_imu.sample.gx_ddps, g_imu.sample.gy_ddps, g_imu.sample.gz_ddps };
    canp_enc_vec3(d, &g);
    tx(CANP_MSG_GYRO, d, st, now);
}

static void task_100ms(uint32_t now)
{
    s_vin_mv = board_vin_mv();
    diag_eval_vin(&s_diag, s_vin_mv);
    bool timeout = false;
    bool any_seen = false;
    for (uint8_t n = 0; n < CANP_MAX_NODES; n++) {
        if (n == s_node) continue;
        if (canp_peer_poll(&s_peer[n], now)) {
            printf("[can] peer node %u TIMEOUT\r\n", n);
        }
        if (s_peer[n].seen) {
            any_seen = true;
            if (!s_peer[n].alive) timeout = true;
        }
    }
    (void)any_seen;
    /* a peer that was never seen is not a fault (single board on the bench) */
    diag_set(&s_diag, FAULT_PEER_TIMEOUT, timeout);
    if (s_diag.state == NODE_STATE_INIT) {
        return;
    }
    uint8_t d[8];
    canp_heartbeat_t hb = { s_node, s_diag.state, s_diag.active, peers_alive_mask(), CANP_FW_VERSION };
    canp_enc_heartbeat(d, &hb);
    tx(CANP_MSG_HEARTBEAT, d, s_diag.state == NODE_STATE_DEGRADED ? CANP_ST_DEGRADED : 0u, now);
    canp_board_t b = { s_vin_mv, g_imu.sample.temp_cdeg, (uint16_t)(now / 1000u) };
    canp_enc_board(d, &b);
    tx(CANP_MSG_BOARD, d, (s_vin_mv ? CANP_ST_DATA_VALID : 0u), now);
}

static const char *state_name(node_state_t s)
{
    static const char *n[] = { "INIT", "RUN", "DEGRADED", "FAULT" };
    return n[s & 3u];
}

static void task_1000ms(uint32_t now)
{
    s_mcu_temp = board_mcu_temp_c();
    diag_set(&s_diag, FAULT_MCU_TEMP, s_mcu_temp != INT16_MIN && s_mcu_temp > 100);
    can_status_t cs;
    can_get_status(&cs);
    if (s_diag.state != NODE_STATE_INIT) {
        uint8_t d[8];
        canp_diag_t dg = {
            .tec = cs.tec, .rec = cs.rec,
            .proto_flags = (uint8_t)((cs.warning ? CANP_PF_WARNING : 0u) | (cs.passive ? CANP_PF_PASSIVE : 0u) |
                                     (cs.busoff ? CANP_PF_BUSOFF : 0u) |
                                     ((uint8_t)(cs.lec << CANP_PF_LEC_SHIFT) & CANP_PF_LEC_MASK)),
            .busoff_count = s_diag.busoff_count, .e2e_errors = s_diag.e2e_errors,
            .reset_cause = (uint8_t)s_diag.reset_cause };
        canp_enc_diag(d, &dg);
        tx(CANP_MSG_DIAG, d, 0u, now);
    }
    printf("node %u %-8s faults act=0x%04X lat=0x%04X | VIN %u mV MCU %d C | "
           "acc %d %d %d mg | peers 0x%X | TEC %u REC %u tx %lu rx %lu\r\n",
           s_node, state_name(s_diag.state), s_diag.active, s_diag.latched, s_vin_mv, s_mcu_temp,
           g_imu.sample.ax_mg, g_imu.sample.ay_mg, g_imu.sample.az_mg, peers_alive_mask(),
           cs.tec, cs.rec, (unsigned long)cs.tx_ok, (unsigned long)cs.rx_ok);
    for (uint8_t n = 0; n < CANP_MAX_NODES; n++) {
        if (n != s_node && s_peer[n].alive) {
            printf("   peer %u %-8s faults 0x%04X acc %d %d %d mg\r\n", n, state_name(s_peer[n].state),
                   s_peer[n].faults, s_peer_accel[n].x, s_peer_accel[n].y, s_peer_accel[n].z);
        }
    }
}

static task_t s_tasks[] = {
    { 10u, 0u, task_10ms },
    { 20u, 3u, task_20ms },      /* offsets spread the load */
    { 100u, 7u, task_100ms },
    { 1000u, 13u, task_1000ms },
};

/* -------------------------------------------------------------- public */
void app_init(uint8_t node_id, reset_cause_t cause, bool hse_ok)
{
    uint32_t now = HAL_GetTick();
    s_node = node_id & 3u;
    memset(s_peer, 0, sizeof s_peer);
    memset(s_rx, 0, sizeof s_rx);
    diag_init(&s_diag, cause, now);
    diag_set(&s_diag, FAULT_HSE, !hse_ok);
    (void)imu_init(&g_imu, now);
    for (size_t i = 0; i < sizeof s_tasks / sizeof s_tasks[0]; i++) {
        s_tasks[i].next_ms = now + s_tasks[i].next_ms;
    }
    s_last_10ms_run = now;
    s_init_done = true;
    printf("\r\nSTM32 CAN ECU fw %u.%u  node %u  reset cause %u  clock %s  IMU WHO_AM_I 0x%02X\r\n",
           CANP_FW_VERSION >> 4, CANP_FW_VERSION & 15u, s_node, (unsigned)cause,
           hse_ok ? "HSE 8 MHz" : "HSI16 FALLBACK", g_imu.who_am_i);
}

void app_note_hse_failure(void)
{
    diag_set(&s_diag, FAULT_HSE, true);
}

void app_run(void)
{
    uint32_t now = HAL_GetTick();
    for (size_t i = 0; i < sizeof s_tasks / sizeof s_tasks[0]; i++) {
        task_t *t = &s_tasks[i];
        if ((int32_t)(now - t->next_ms) >= 0) {
            t->next_ms += t->period_ms;
            if ((int32_t)(now - t->next_ms) >= 0) {
                t->next_ms = now + t->period_ms;    /* overrun: re-align, don't burst */
            }
            t->fn(now);
        }
    }
}

bool app_alive(uint32_t now_ms)
{
    return (uint32_t)(now_ms - s_last_10ms_run) < 100u;
}
