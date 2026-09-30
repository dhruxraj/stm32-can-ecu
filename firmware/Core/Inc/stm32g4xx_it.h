#ifndef STM32G4XX_IT_H
#define STM32G4XX_IT_H
void NMI_Handler(void);
void HardFault_Handler(void);
void MemManage_Handler(void);
void BusFault_Handler(void);
void UsageFault_Handler(void);
void SVC_Handler(void);
void DebugMon_Handler(void);
void PendSV_Handler(void);
void SysTick_Handler(void);
void FDCAN1_IT0_IRQHandler(void);
#endif
