/**
 * @file    main.c
 * @brief   STM32 CAN ECU firmware entry point (STM32G431CBT6, STM32Cube HAL).
 *
 * Start-up order:
 *   HAL + clocks (HSE 8 MHz -> PLL 170 MHz, fallback HSI16) -> UCPD dead-battery
 *   pull-downs off -> GPIO (transceiver kept silent) -> UART console -> reset
 *   cause -> watchdog (~1 s) -> ADC -> I2C + IMU -> FDCAN -> application loop.
 */
#include "main.h"

#include <stdio.h>

#include "app.h"
#include "board.h"
#include "can.h"
#include "debug.h"
#include "diagnostics.h"

I2C_HandleTypeDef  hi2c1;
IWDG_HandleTypeDef hiwdg;
volatile bool      g_hse_failed;

static reset_cause_t read_reset_cause(void)
{
    reset_cause_t c = RESET_CAUSE_UNKNOWN;
    if (__HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST))      c = RESET_CAUSE_IWDG;
    else if (__HAL_RCC_GET_FLAG(RCC_FLAG_WWDGRST)) c = RESET_CAUSE_WWDG;
    else if (__HAL_RCC_GET_FLAG(RCC_FLAG_LPWRRST)) c = RESET_CAUSE_LOW_POWER;
    else if (__HAL_RCC_GET_FLAG(RCC_FLAG_SFTRST))  c = RESET_CAUSE_SOFTWARE;
    else if (__HAL_RCC_GET_FLAG(RCC_FLAG_OBLRST))  c = RESET_CAUSE_OPTION_BYTE;
    else if (__HAL_RCC_GET_FLAG(RCC_FLAG_BORRST))  c = RESET_CAUSE_POWER_ON;
    else if (__HAL_RCC_GET_FLAG(RCC_FLAG_PINRST))  c = RESET_CAUSE_PIN;
    __HAL_RCC_CLEAR_RESET_FLAGS();
    return c;
}

static bool i2c1_init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.Timing = 0x10320309;          /* 400 kHz @ I2CCLK = HSI16 (RM0440 example) */
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK) return false;
    if (HAL_I2CEx_ConfigAnalogFilter(&hi2c1, I2C_ANALOGFILTER_ENABLE) != HAL_OK) return false;
    return HAL_I2CEx_ConfigDigitalFilter(&hi2c1, 0) == HAL_OK;
}

static void iwdg_init(void)
{
    /* LSI ~32 kHz / 32 = 1 kHz -> reload 1000 = ~1.0 s (LSI tolerance applies) */
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_32;
    hiwdg.Init.Window = IWDG_WINDOW_DISABLE;
    hiwdg.Init.Reload = 1000;
    __HAL_DBGMCU_FREEZE_IWDG();              /* do not reset while halted in the debugger */
    if (HAL_IWDG_Init(&hiwdg) != HAL_OK) {
        Error_Handler();
    }
}

int main(void)
{
    HAL_Init();
    bool hse_ok = SystemClock_Config();
    HAL_PWREx_DisableUCPDDeadBattery();      /* PB4/PB6 UCPD pull-downs off */
    board_gpio_init();
    (void)debug_init();
    reset_cause_t cause = read_reset_cause();
    iwdg_init();
    if (!board_adc_init()) {
        printf("ADC init failed\r\n");
    }
    if (!i2c1_init()) {
        printf("I2C init failed\r\n");
    }
    uint8_t node = board_node_id();
    if (!can_init(node)) {
        printf("FDCAN init failed\r\n");
        Error_Handler();
    }
    app_init(node, cause, hse_ok);

    for (;;) {
        if (g_hse_failed) {
            g_hse_failed = false;
            (void)SystemClock_Config();        /* rebuild PLL from HSI16 */
            app_note_hse_failure();
        }
        app_run();
        if (app_alive(HAL_GetTick())) {
            (void)HAL_IWDG_Refresh(&hiwdg);
        }
    }
}

/**
 * HSE 8 MHz / M2 * N85 / R2 = 170 MHz, voltage range 1 boost, 4 wait states.
 * If the crystal does not start, the same PLL is built from HSI16 / M4.
 * FDCAN, USART2 and ADC run from PCLK1/HCLK = 170 MHz in both cases, so the
 * CAN bit timing is unchanged (HSI16 accuracy is +-1 %: marginal for CAN,
 * therefore flagged as FAULT_HSE).
 */
bool SystemClock_Config(void)
{
    RCC_OscInitTypeDef o = {0};
    RCC_ClkInitTypeDef c = {0};
    bool hse_ok = true;

    HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1_BOOST);

    o.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_HSI;
    o.HSEState = g_hse_failed ? RCC_HSE_OFF : RCC_HSE_ON;
    o.HSIState = RCC_HSI_ON;
    o.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLM = RCC_PLLM_DIV2;
    o.PLL.PLLN = 85;
    o.PLL.PLLP = RCC_PLLP_DIV2;
    o.PLL.PLLQ = RCC_PLLQ_DIV2;
    o.PLL.PLLR = RCC_PLLR_DIV2;
    if (g_hse_failed || HAL_RCC_OscConfig(&o) != HAL_OK) {
        hse_ok = false;
        o.OscillatorType = RCC_OSCILLATORTYPE_HSI;
        o.HSEState = RCC_HSE_OFF;
        o.PLL.PLLSource = RCC_PLLSOURCE_HSI;
        o.PLL.PLLM = RCC_PLLM_DIV4;
        if (HAL_RCC_OscConfig(&o) != HAL_OK) {
            Error_Handler();
        }
    }
    c.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.AHBCLKDivider = RCC_SYSCLK_DIV1;
    c.APB1CLKDivider = RCC_HCLK_DIV1;
    c.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&c, FLASH_LATENCY_4) != HAL_OK) {
        Error_Handler();
    }
    if (hse_ok) {
        HAL_RCC_EnableCSS();                 /* HSE failure -> NMI -> HAL_RCC_CSSCallback */
    }
    return hse_ok;
}

void HAL_RCC_CSSCallback(void)
{
    g_hse_failed = true;                     /* hardware already switched SYSCLK to HSI16 */
}

void Error_Handler(void)
{
    __disable_irq();
    /* FAULT LED on, STATUS off; the watchdog resets the MCU after ~1 s */
    HAL_GPIO_WritePin(LED_FAULT_PORT, LED_FAULT_PIN, GPIO_PIN_SET);
    HAL_GPIO_WritePin(LED_STATUS_PORT, LED_STATUS_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CAN_S_PORT, CAN_S_PIN, GPIO_PIN_SET);   /* transceiver silent */
    for (;;) {
    }
}

#ifdef USE_FULL_ASSERT
void assert_failed(uint8_t *file, uint32_t line)
{
    printf("assert failed %s:%lu\r\n", (const char *)file, (unsigned long)line);
    Error_Handler();
}
#endif
