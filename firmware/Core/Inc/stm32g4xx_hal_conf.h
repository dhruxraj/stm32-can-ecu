/**
 * @file    stm32g4xx_hal_conf.h
 * @brief   HAL configuration for the STM32 CAN ECU (based on ST's
 *          stm32g4xx_hal_conf_template.h, only the modules that are used).
 */
#ifndef STM32G4XX_HAL_CONF_H
#define STM32G4XX_HAL_CONF_H

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------- module selection ------------------------------ */
#define HAL_MODULE_ENABLED
#define HAL_ADC_MODULE_ENABLED
#define HAL_FDCAN_MODULE_ENABLED
#define HAL_I2C_MODULE_ENABLED
#define HAL_IWDG_MODULE_ENABLED
#define HAL_UART_MODULE_ENABLED
#define HAL_GPIO_MODULE_ENABLED
#define HAL_EXTI_MODULE_ENABLED
#define HAL_DMA_MODULE_ENABLED
#define HAL_RCC_MODULE_ENABLED
#define HAL_FLASH_MODULE_ENABLED
#define HAL_PWR_MODULE_ENABLED
#define HAL_CORTEX_MODULE_ENABLED

/* ------------------------- register callbacks ---------------------------- */
#define USE_HAL_ADC_REGISTER_CALLBACKS    0U
#define USE_HAL_FDCAN_REGISTER_CALLBACKS  0U
#define USE_HAL_I2C_REGISTER_CALLBACKS    0U
#define USE_HAL_UART_REGISTER_CALLBACKS   0U

/* ------------------------- oscillator values ----------------------------- */
#if !defined(HSE_VALUE)
#define HSE_VALUE              8000000UL   /* Y1: 8 MHz crystal */
#endif
#if !defined(HSE_STARTUP_TIMEOUT)
#define HSE_STARTUP_TIMEOUT    100UL
#endif
#if !defined(HSI_VALUE)
#define HSI_VALUE              16000000UL
#endif
#if !defined(HSI48_VALUE)
#define HSI48_VALUE            48000000UL
#endif
#if !defined(LSI_VALUE)
#define LSI_VALUE              32000UL
#endif
#if !defined(LSE_VALUE)
#define LSE_VALUE              32768UL     /* no LSE fitted */
#endif
#if !defined(LSE_STARTUP_TIMEOUT)
#define LSE_STARTUP_TIMEOUT    5000UL
#endif
#if !defined(EXTERNAL_CLOCK_VALUE)
#define EXTERNAL_CLOCK_VALUE   12288000UL
#endif

/* ------------------------- system configuration -------------------------- */
#define VDD_VALUE                    3300UL
#define TICK_INT_PRIORITY            0UL
#define USE_RTOS                     0U
#define PREFETCH_ENABLE              0U
#define INSTRUCTION_CACHE_ENABLE     1U
#define DATA_CACHE_ENABLE            1U
#define USE_SPI_CRC                  0U

/* #define USE_FULL_ASSERT 1U */

/* ------------------------- includes -------------------------------------- */
#ifdef HAL_RCC_MODULE_ENABLED
#include "stm32g4xx_hal_rcc.h"
#endif
#ifdef HAL_GPIO_MODULE_ENABLED
#include "stm32g4xx_hal_gpio.h"
#endif
#ifdef HAL_DMA_MODULE_ENABLED
#include "stm32g4xx_hal_dma.h"
#endif
#ifdef HAL_CORTEX_MODULE_ENABLED
#include "stm32g4xx_hal_cortex.h"
#endif
#ifdef HAL_ADC_MODULE_ENABLED
#include "stm32g4xx_hal_adc.h"
#endif
#ifdef HAL_EXTI_MODULE_ENABLED
#include "stm32g4xx_hal_exti.h"
#endif
#ifdef HAL_FDCAN_MODULE_ENABLED
#include "stm32g4xx_hal_fdcan.h"
#endif
#ifdef HAL_FLASH_MODULE_ENABLED
#include "stm32g4xx_hal_flash.h"
#endif
#ifdef HAL_I2C_MODULE_ENABLED
#include "stm32g4xx_hal_i2c.h"
#endif
#ifdef HAL_IWDG_MODULE_ENABLED
#include "stm32g4xx_hal_iwdg.h"
#endif
#ifdef HAL_PWR_MODULE_ENABLED
#include "stm32g4xx_hal_pwr.h"
#endif
#ifdef HAL_UART_MODULE_ENABLED
#include "stm32g4xx_hal_uart.h"
#endif

#ifdef USE_FULL_ASSERT
#define assert_param(expr) ((expr) ? (void)0U : assert_failed((uint8_t *)__FILE__, __LINE__))
void assert_failed(uint8_t *file, uint32_t line);
#else
#define assert_param(expr) ((void)0U)
#endif

#ifdef __cplusplus
}
#endif
#endif /* STM32G4XX_HAL_CONF_H */
