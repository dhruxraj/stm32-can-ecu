/**
 * @file    debug.h
 * @brief   USART2 (PA2 TX / PA3 RX, 115200 8N1) debug console, printf redirect.
 */
#ifndef DEBUG_H
#define DEBUG_H
#include <stdbool.h>
bool debug_init(void);
#endif
