/**
 * @file    diagnostics.h
 * @brief   Fault flags, fault latching and node state machine (pure C, host-testable).
 */
#ifndef DIAGNOSTICS_H
#define DIAGNOSTICS_H

#include <stdbool.h>
#include <stdint.h>
#include "can_protocol.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Fault bits - transmitted in the heartbeat (bytes 2..3) and printed on UART */
#define FAULT_IMU_COMM       (1u << 0)   /* IMU not answering / wrong WHO_AM_I / I2C errors */
#define FAULT_IMU_DATA       (1u << 1)   /* IMU data stuck or implausible                   */
#define FAULT_CAN_BUSOFF     (1u << 2)   /* FDCAN in bus-off (recovery running)             */
#define FAULT_CAN_PASSIVE    (1u << 3)   /* FDCAN error passive (e.g. no other node ACKs)   */
#define FAULT_PEER_TIMEOUT   (1u << 4)   /* a previously seen peer stopped sending          */
#define FAULT_CAN_E2E        (1u << 5)   /* CRC / counter / DLC errors in the last second   */
#define FAULT_VIN_LOW        (1u << 6)   /* VIN < 7.5 V (regulator dropout region)          */
#define FAULT_VIN_HIGH       (1u << 7)   /* VIN > 18.5 V                                    */
#define FAULT_HSE            (1u << 8)   /* crystal failed, running on HSI16 (+-1 %)        */
#define FAULT_WDG_RESET      (1u << 9)   /* last reset was caused by the watchdog (latched) */
#define FAULT_CAN_TX_OVF     (1u << 10)  /* TX FIFO full, frame dropped                     */
#define FAULT_MCU_TEMP       (1u << 11)  /* MCU die temperature > 100 degC                  */
#define FAULT_ID_CONFLICT    (1u << 12)  /* another node transmits with our node ID         */

#define FAULT_CRITICAL_MASK  (FAULT_CAN_BUSOFF)

typedef enum {
    RESET_CAUSE_UNKNOWN = 0,
    RESET_CAUSE_POWER_ON,     /* BOR / POR */
    RESET_CAUSE_PIN,          /* NRST pin (button, debugger) */
    RESET_CAUSE_SOFTWARE,
    RESET_CAUSE_IWDG,
    RESET_CAUSE_WWDG,
    RESET_CAUSE_LOW_POWER,
    RESET_CAUSE_OPTION_BYTE
} reset_cause_t;

#define DIAG_INIT_MIN_MS      200u
#define DIAG_E2E_HOLD_MS     1000u
#define DIAG_TXOVF_HOLD_MS   1000u
#define DIAG_VIN_LOW_SET_MV  7500u
#define DIAG_VIN_LOW_CLR_MV  7800u
#define DIAG_VIN_HIGH_SET_MV 18500u
#define DIAG_VIN_HIGH_CLR_MV 18000u

typedef struct {
    uint16_t      active;          /* currently present faults            */
    uint16_t      latched;         /* history since power-up / last clear */
    node_state_t  state;
    uint32_t      boot_ms;
    uint32_t      last_e2e_ms;
    uint32_t      last_txovf_ms;
    uint8_t       e2e_errors;      /* saturating counter (diag frame)     */
    uint8_t       busoff_count;    /* saturating counter (diag frame)     */
    reset_cause_t reset_cause;
} diag_t;

void         diag_init(diag_t *d, reset_cause_t cause, uint32_t now_ms);
void         diag_set(diag_t *d, uint16_t mask, bool present);
void         diag_clear_latched(diag_t *d);
void         diag_note_e2e_error(diag_t *d, uint32_t now_ms);
void         diag_note_tx_overflow(diag_t *d, uint32_t now_ms);
void         diag_note_busoff(diag_t *d);
void         diag_eval_vin(diag_t *d, uint16_t vin_mv);
node_state_t diag_update(diag_t *d, uint32_t now_ms, bool init_done);

#ifdef __cplusplus
}
#endif
#endif /* DIAGNOSTICS_H */
