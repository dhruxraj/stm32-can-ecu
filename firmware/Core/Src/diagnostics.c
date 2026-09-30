/**
 * @file    diagnostics.c
 * @brief   Fault management and node state machine.
 *
 *   INIT      -> after init_done and >= DIAG_INIT_MIN_MS since boot
 *   RUN       -> no active fault
 *   DEGRADED  -> any non-critical active fault (IMU, peer timeout, E2E, VIN, HSE ...)
 *   FAULT     -> any critical active fault (FAULT_CRITICAL_MASK, i.e. CAN bus-off)
 * Faults are "active" while present and additionally "latched" until cleared by
 * CLEAR_FAULTS command or a long press of the USER button.
 */
#include "diagnostics.h"

void diag_init(diag_t *d, reset_cause_t cause, uint32_t now_ms)
{
    d->active = 0u;
    d->latched = 0u;
    d->state = NODE_STATE_INIT;
    d->boot_ms = now_ms;
    d->last_e2e_ms = 0u;
    d->last_txovf_ms = 0u;
    d->e2e_errors = 0u;
    d->busoff_count = 0u;
    d->reset_cause = cause;
    if (cause == RESET_CAUSE_IWDG || cause == RESET_CAUSE_WWDG) {
        d->latched |= FAULT_WDG_RESET;
    }
}

void diag_set(diag_t *d, uint16_t mask, bool present)
{
    if (present) {
        d->active |= mask;
        d->latched |= mask;
    } else {
        d->active &= (uint16_t)~mask;
    }
}

void diag_clear_latched(diag_t *d)
{
    d->latched = d->active;
    d->e2e_errors = 0u;
}

void diag_note_e2e_error(diag_t *d, uint32_t now_ms)
{
    d->last_e2e_ms = now_ms;
    if (d->e2e_errors < 255u) {
        d->e2e_errors++;
    }
    diag_set(d, FAULT_CAN_E2E, true);
}

void diag_note_tx_overflow(diag_t *d, uint32_t now_ms)
{
    d->last_txovf_ms = now_ms;
    diag_set(d, FAULT_CAN_TX_OVF, true);
}

void diag_note_busoff(diag_t *d)
{
    if (d->busoff_count < 255u) {
        d->busoff_count++;
    }
}

void diag_eval_vin(diag_t *d, uint16_t vin_mv)
{
    if (vin_mv < DIAG_VIN_LOW_SET_MV) {
        diag_set(d, FAULT_VIN_LOW, true);
    } else if (vin_mv > DIAG_VIN_LOW_CLR_MV) {
        diag_set(d, FAULT_VIN_LOW, false);
    }
    if (vin_mv > DIAG_VIN_HIGH_SET_MV) {
        diag_set(d, FAULT_VIN_HIGH, true);
    } else if (vin_mv < DIAG_VIN_HIGH_CLR_MV) {
        diag_set(d, FAULT_VIN_HIGH, false);
    }
}

node_state_t diag_update(diag_t *d, uint32_t now_ms, bool init_done)
{
    if ((d->active & FAULT_CAN_E2E) && (uint32_t)(now_ms - d->last_e2e_ms) > DIAG_E2E_HOLD_MS) {
        diag_set(d, FAULT_CAN_E2E, false);
    }
    if ((d->active & FAULT_CAN_TX_OVF) && (uint32_t)(now_ms - d->last_txovf_ms) > DIAG_TXOVF_HOLD_MS) {
        diag_set(d, FAULT_CAN_TX_OVF, false);
    }
    if (d->state == NODE_STATE_INIT) {
        if (!init_done || (uint32_t)(now_ms - d->boot_ms) < DIAG_INIT_MIN_MS) {
            return d->state;
        }
    }
    if (d->active & FAULT_CRITICAL_MASK) {
        d->state = NODE_STATE_FAULT;
    } else if (d->active) {
        d->state = NODE_STATE_DEGRADED;
    } else {
        d->state = NODE_STATE_RUN;
    }
    return d->state;
}
