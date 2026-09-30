/**
 * Host unit tests for the hardware-independent firmware modules:
 * can_protocol.c, diagnostics.c and the conversion/plausibility part of imu.c.
 * Build & run:  make -C firmware/tests
 */
#include <stdio.h>
#include <string.h>
#include "can_protocol.h"
#include "diagnostics.h"
#include "imu.h"

static int g_fail, g_pass;
#define CHECK(c) do { if (c) g_pass++; else { g_fail++; printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #c); } } while (0)

static void test_crc(void)
{
    const uint8_t v[] = "123456789";
    CHECK(canp_crc8_j1850(v, 9) == 0x4B);          /* CRC-8/SAE-J1850 check value */
    CHECK(canp_crc8_j1850(v, 0) == 0x00);
}

static void test_ids(void)
{
    uint8_t n; canp_msg_t m;
    CHECK(canp_id(0, CANP_MSG_HEARTBEAT) == 0x100);
    CHECK(canp_id(1, CANP_MSG_ACCEL) == 0x111);
    CHECK(canp_id(3, CANP_MSG_DIAG) == 0x134);
    CHECK(canp_decode_id(0x123, &n, &m) && n == 2 && m == CANP_MSG_BOARD);
    CHECK(!canp_decode_id(0x105, &n, &m));
    CHECK(!canp_decode_id(0x140, &n, &m));
    CHECK(!canp_decode_id(0x0FF, &n, &m));
    CHECK(canp_cmd_id(2) == 0x0F2);
    CHECK(canp_cmd_id(0xFF) == 0x0FF);
    CHECK(canp_is_cmd_for(0x0F1, 1) && canp_is_cmd_for(0x0FF, 3) && !canp_is_cmd_for(0x0F2, 1));
}

static void test_seal_check(void)
{
    uint8_t d[8], e[8];
    uint8_t cnt = 0;
    canp_rx_state_t st = {0};
    canp_heartbeat_t hb = { 1, NODE_STATE_RUN, 0x0010, 0x01, CANP_FW_VERSION }, o;
    uint16_t id = canp_id(1, CANP_MSG_HEARTBEAT);
    canp_enc_heartbeat(d, &hb);
    canp_seal(id, d, &cnt, CANP_ST_DEGRADED);
    CHECK(cnt == 1);
    CHECK(canp_counter(d) == 0 && canp_status(d) == CANP_ST_DEGRADED);
    CHECK(canp_check(id, 8, d, &st) == CANP_OK);
    canp_dec_heartbeat(d, &o);
    CHECK(o.node_id == 1 && o.state == NODE_STATE_RUN && o.faults == 0x0010 && o.peers_alive == 1 && o.fw_version == 0x10);
    CHECK(canp_check(id, 8, d, &st) == CANP_ERR_COUNTER_REPEAT);   /* replayed frame */
    memcpy(e, d, 8); e[2] ^= 0x04;
    CHECK(canp_check(id, 8, e, &st) == CANP_ERR_CRC);             /* single bit flip */
    CHECK(canp_check(id + 1, 8, d, &st) == CANP_ERR_CRC);         /* ID is protected */
    CHECK(canp_check(id, 7, d, &st) == CANP_ERR_DLC);
    canp_enc_heartbeat(d, &hb); canp_seal(id, d, &cnt, 0);          /* counter 1 */
    CHECK(canp_check(id, 8, d, &st) == CANP_OK);
    cnt = 5; canp_enc_heartbeat(d, &hb); canp_seal(id, d, &cnt, 0); /* counter 5: lost 2,3,4 */
    CHECK(canp_check(id, 8, d, &st) == CANP_OK_COUNTER_JUMP && st.lost == 3);
    /* wrap 15 -> 0 */
    canp_rx_state_t w = {0};
    cnt = 15; canp_enc_heartbeat(d, &hb); canp_seal(id, d, &cnt, 0);
    CHECK(cnt == 0 && canp_check(id, 8, d, &w) == CANP_OK);
    canp_enc_heartbeat(d, &hb); canp_seal(id, d, &cnt, 0);
    CHECK(canp_check(id, 8, d, &w) == CANP_OK && w.lost == 0);
    CHECK(st.errors == 4);
}

static void test_payloads(void)
{
    uint8_t d[8] = {0};
    canp_vec3_t v = { 0x1234, -1000, -32768 }, vo;
    canp_enc_vec3(d, &v);
    CHECK(d[0] == 0x34 && d[1] == 0x12);                            /* little endian */
    canp_dec_vec3(d, &vo);
    CHECK(vo.x == 0x1234 && vo.y == -1000 && vo.z == -32768);
    canp_board_t b = { 12034, -1234, 65535 }, bo;
    canp_enc_board(d, &b); canp_dec_board(d, &bo);
    CHECK(bo.vin_mv == 12034 && bo.imu_temp_cdeg == -1234 && bo.uptime_s == 65535);
    canp_diag_t g = { 128, 5, 0x0A, 3, 7, RESET_CAUSE_IWDG }, go;
    canp_enc_diag(d, &g); canp_dec_diag(d, &go);
    CHECK(memcmp(&g, &go, sizeof g) == 0);
    canp_command_t c = { CANP_CMD_IDENTIFY, 2, 9 }, co;
    canp_enc_command(d, &c); canp_dec_command(d, &co);
    CHECK(co.cmd == CANP_CMD_IDENTIFY && co.source_node == 2 && co.arg == 9 && d[3] == 0 && d[5] == 0);
}

static void test_peer(void)
{
    canp_peer_t p = {0};
    canp_heartbeat_t hb = { 0, NODE_STATE_RUN, 0, 0, 0x10 };
    CHECK(!canp_peer_poll(&p, 5000));                  /* never seen: no timeout */
    canp_peer_rx(&p, 1000, &hb);
    CHECK(!canp_peer_poll(&p, 1300));
    CHECK(canp_peer_poll(&p, 1301));
    CHECK(!canp_peer_poll(&p, 1400) && !p.alive && p.seen);
    canp_peer_rx(&p, 0xFFFFFF00u, &hb);                /* tick wrap-around */
    CHECK(!canp_peer_poll(&p, 0x00000010u));
    CHECK(canp_peer_poll(&p, 0x00000040u));
}

static void test_diag(void)
{
    diag_t d;
    diag_init(&d, RESET_CAUSE_POWER_ON, 0);
    CHECK(diag_update(&d, 100, true) == NODE_STATE_INIT);
    CHECK(diag_update(&d, 250, false) == NODE_STATE_INIT);
    CHECK(diag_update(&d, 250, true) == NODE_STATE_RUN);
    diag_eval_vin(&d, 7400);
    CHECK((d.active & FAULT_VIN_LOW) && diag_update(&d, 260, true) == NODE_STATE_DEGRADED);
    diag_eval_vin(&d, 7700);                           /* inside hysteresis: stays */
    CHECK(d.active & FAULT_VIN_LOW);
    diag_eval_vin(&d, 12000);
    CHECK(!(d.active & FAULT_VIN_LOW) && (d.latched & FAULT_VIN_LOW));
    diag_eval_vin(&d, 19000);
    CHECK(d.active & FAULT_VIN_HIGH);
    diag_eval_vin(&d, 12000);
    diag_note_e2e_error(&d, 1000);
    CHECK(diag_update(&d, 1500, true) == NODE_STATE_DEGRADED);
    CHECK(diag_update(&d, 2001, true) == NODE_STATE_RUN && (d.latched & FAULT_CAN_E2E) && d.e2e_errors == 1);
    diag_set(&d, FAULT_CAN_BUSOFF, true);
    CHECK(diag_update(&d, 2100, true) == NODE_STATE_FAULT);
    diag_clear_latched(&d);
    CHECK(d.latched == FAULT_CAN_BUSOFF && d.e2e_errors == 0);
    diag_set(&d, FAULT_CAN_BUSOFF, false);
    CHECK(diag_update(&d, 2200, true) == NODE_STATE_RUN);
    diag_init(&d, RESET_CAUSE_IWDG, 0);
    CHECK((d.latched & FAULT_WDG_RESET) && !(d.active & FAULT_WDG_RESET));
    for (int i = 0; i < 300; i++) diag_note_busoff(&d);
    CHECK(d.busoff_count == 255);
}

static void test_imu(void)
{
    CHECK(imu_accel_mg(8196) == 999);
    CHECK(imu_accel_mg(-32768) == -3997);
    CHECK(imu_gyro_ddps(5714) == 999);
    CHECK(imu_temp_cdeg(0) == 2500 && imu_temp_cdeg(256) == 2600 && imu_temp_cdeg(-512) == 2300);
    uint8_t b[14] = { 0x00, 0x01,  0x10, 0x00, 0x20, 0x00, 0x30, 0x00,  0x04, 0x20, 0x00, 0x00, 0xFC, 0xDF };
    imu_sample_t s; int16_t raw[6];
    imu_convert(b, &s, raw);
    CHECK(raw[0] == 0x2004 && raw[1] == 0 && raw[2] == (int16_t)0xDFFC && raw[3] == 0x10 && raw[5] == 0x30);
    CHECK(s.temp_cdeg == 2600 && s.ax_mg == imu_accel_mg(0x2004));
    imu_t imu; memset(&imu, 0, sizeof imu);
    int16_t r[6] = { 10, 20, 1000, 1, 2, 3 };
    int ok = 1;
    for (unsigned i = 0; i < IMU_STUCK_LIMIT; i++) ok &= imu_plausible(&imu, r);
    CHECK(ok);                                          /* 49 repeats still accepted */
    CHECK(!imu_plausible(&imu, r));                     /* 50th repeat -> stuck      */
    r[0] = 11;
    CHECK(imu_plausible(&imu, r));                      /* recovers on change        */
    int16_t z[6] = { 0, 0, 0, 1, 2, 3 };
    CHECK(!imu_plausible(&imu, z));
}

static void print_vectors(void)
{
    /* golden frames, used by docs/CAN_PROTOCOL.md and tools/test_tools.py */
    uint8_t d[8], cnt = 3;
    canp_heartbeat_t hb = { 1, NODE_STATE_RUN, 0x0000, 0x01, CANP_FW_VERSION };
    canp_enc_heartbeat(d, &hb);
    canp_seal(0x110, d, &cnt, 0);
    printf("VECTOR 0x110");
    for (int i = 0; i < 8; i++) printf(" %02X", d[i]);
    printf("\n");
    canp_vec3_t v = { 12, -35, 998 }; cnt = 7;
    canp_enc_vec3(d, &v); canp_seal(0x101, d, &cnt, CANP_ST_DATA_VALID);
    printf("VECTOR 0x101");
    for (int i = 0; i < 8; i++) printf(" %02X", d[i]);
    printf("\n");
}

int main(void)
{
    test_crc(); test_ids(); test_seal_check(); test_payloads(); test_peer(); test_diag(); test_imu();
    print_vectors();
    printf("%d checks passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
