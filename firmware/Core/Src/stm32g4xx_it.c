/**
 * @file    stm32g4xx_it.c
 * @brief   Exception and interrupt handlers.
 */
#include "stm32g4xx_it.h"
#include "main.h"

extern FDCAN_HandleTypeDef hfdcan1;

void NMI_Handler(void)
{
    HAL_RCC_NMI_IRQHandler();                /* clock security system (HSE failure) */
}

static void fault_loop(void)
{
    /* FAULT LED on and spin: the independent watchdog resets the MCU */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, GPIO_PIN_SET);
    for (;;) {
    }
}

void HardFault_Handler(void)  { fault_loop(); }
void MemManage_Handler(void)  { fault_loop(); }
void BusFault_Handler(void)   { fault_loop(); }
void UsageFault_Handler(void) { fault_loop(); }
void SVC_Handler(void)        {}
void DebugMon_Handler(void)   {}
void PendSV_Handler(void)     {}

void SysTick_Handler(void)
{
    HAL_IncTick();
}

void FDCAN1_IT0_IRQHandler(void)
{
    HAL_FDCAN_IRQHandler(&hfdcan1);
}
