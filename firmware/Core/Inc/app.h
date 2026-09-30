/**
 * @file    app.h
 * @brief   Application: cooperative scheduler, CAN messaging, LEDs, button.
 */
#ifndef APP_H
#define APP_H

#include <stdbool.h>
#include <stdint.h>
#include "diagnostics.h"

void app_init(uint8_t node_id, reset_cause_t cause, bool hse_ok);
void app_run(void);                 /* call continuously from main loop (non-blocking) */
bool app_alive(uint32_t now_ms);    /* true if the 10 ms task ran recently (watchdog gate) */
void app_note_hse_failure(void);

#endif /* APP_H */
