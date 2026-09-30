/**
 * @file    debug.c
 * @brief   USART2 console on expansion header J5 (pin 3 = TX, pin 4 = RX, pin 2 = GND).
 *          printf() is routed here through newlib's _write().
 */
#include "debug.h"
#include "main.h"

UART_HandleTypeDef huart2;

bool debug_init(void)
{
    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    huart2.Init.ClockPrescaler = UART_PRESCALER_DIV1;
    huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    return HAL_UART_Init(&huart2) == HAL_OK;
}

/* newlib syscall: blocking transmit with a short timeout so a disconnected
 * console can never stall the main loop for long (watchdog is ~1 s). */
int _write(int file, char *ptr, int len)
{
    (void)file;
    if (huart2.Instance == NULL || len <= 0) {
        return len;
    }
    (void)HAL_UART_Transmit(&huart2, (uint8_t *)ptr, (uint16_t)len, 20);
    return len;
}
