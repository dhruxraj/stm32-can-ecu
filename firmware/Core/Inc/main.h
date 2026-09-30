/**
 * @file    main.h
 * @brief   Global HAL handles and error handler of the STM32 CAN ECU firmware.
 */
#ifndef MAIN_H
#define MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32g4xx_hal.h"
#include <stdbool.h>
#include <stdint.h>

extern FDCAN_HandleTypeDef hfdcan1;
extern I2C_HandleTypeDef   hi2c1;
extern UART_HandleTypeDef  huart2;
extern ADC_HandleTypeDef   hadc1;
extern IWDG_HandleTypeDef  hiwdg;

extern volatile bool g_hse_failed;   /* set by the clock security system (NMI) */

void Error_Handler(void);
bool SystemClock_Config(void);       /* true = HSE crystal, false = HSI fallback */

#ifdef __cplusplus
}
#endif
#endif /* MAIN_H */
