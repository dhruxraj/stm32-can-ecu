/*
 * Minimal STM32G4 HAL *stub* for PC-side compile checks only (tests/Makefile
 * target "stubcheck").  Declarations mirror the signatures/field names of the
 * STM32CubeG4 HAL that the firmware uses.  NOT functional, NOT for the target.
 */
#ifndef STM32G4XX_HAL_STUB_H
#define STM32G4XX_HAL_STUB_H
#include <stdint.h>
#include <stddef.h>

typedef enum { HAL_OK = 0, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT } HAL_StatusTypeDef;
typedef enum { DISABLE = 0, ENABLE = 1 } FunctionalState;
typedef enum { GPIO_PIN_RESET = 0, GPIO_PIN_SET } GPIO_PinState;
typedef int IRQn_Type;
#define FDCAN1_IT0_IRQn 21

#define __IO volatile
typedef struct { __IO uint32_t MODER, OTYPER, OSPEEDR, PUPDR, IDR, ODR, BSRR; } GPIO_TypeDef;
typedef struct { __IO uint32_t CCCR; } FDCAN_GlobalTypeDef;
typedef struct { __IO uint32_t CR1; } I2C_TypeDef;
typedef struct { __IO uint32_t CR1; } USART_TypeDef;
typedef struct { __IO uint32_t ISR; } ADC_TypeDef;
typedef struct { __IO uint32_t KR; } IWDG_TypeDef;
extern GPIO_TypeDef stub_gpio[6];
extern FDCAN_GlobalTypeDef stub_fdcan;
extern I2C_TypeDef stub_i2c; extern USART_TypeDef stub_usart; extern ADC_TypeDef stub_adc; extern IWDG_TypeDef stub_iwdg;
#define GPIOA (&stub_gpio[0])
#define GPIOB (&stub_gpio[1])
#define GPIOC (&stub_gpio[2])
#define GPIOF (&stub_gpio[5])
#define FDCAN1 (&stub_fdcan)
#define I2C1 (&stub_i2c)
#define USART2 (&stub_usart)
#define ADC1 (&stub_adc)
#define IWDG (&stub_iwdg)
#define FDCAN_CCCR_INIT (1UL << 0)
#define CLEAR_BIT(REG, BIT) ((REG) &= ~(BIT))
#define __DMB() __asm__ volatile("" ::: "memory")
#define __disable_irq() do {} while (0)

/* ---- GPIO ---- */
typedef struct { uint32_t Pin, Mode, Pull, Speed, Alternate; } GPIO_InitTypeDef;
#define GPIO_PIN_0 0x0001U
#define GPIO_PIN_1 0x0002U
#define GPIO_PIN_2 0x0004U
#define GPIO_PIN_3 0x0008U
#define GPIO_PIN_4 0x0010U
#define GPIO_PIN_5 0x0020U
#define GPIO_PIN_6 0x0040U
#define GPIO_PIN_7 0x0080U
#define GPIO_PIN_8 0x0100U
#define GPIO_PIN_9 0x0200U
#define GPIO_PIN_10 0x0400U
#define GPIO_PIN_11 0x0800U
#define GPIO_PIN_12 0x1000U
#define GPIO_PIN_13 0x2000U
#define GPIO_PIN_14 0x4000U
#define GPIO_PIN_15 0x8000U
#define GPIO_MODE_INPUT 0U
#define GPIO_MODE_OUTPUT_PP 1U
#define GPIO_MODE_AF_PP 2U
#define GPIO_MODE_AF_OD 0x12U
#define GPIO_MODE_ANALOG 3U
#define GPIO_NOPULL 0U
#define GPIO_PULLUP 1U
#define GPIO_PULLDOWN 2U
#define GPIO_SPEED_FREQ_LOW 0U
#define GPIO_AF4_I2C1 4U
#define GPIO_AF7_USART2 7U
#define GPIO_AF9_FDCAN1 9U
void HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_Init);
void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState);
GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin);

/* ---- core / system ---- */
HAL_StatusTypeDef HAL_Init(void);
uint32_t HAL_GetTick(void);
void HAL_IncTick(void);
void HAL_Delay(uint32_t Delay);
void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t PreemptPriority, uint32_t SubPriority);
void HAL_NVIC_EnableIRQ(IRQn_Type IRQn);
#define __HAL_DBGMCU_FREEZE_IWDG() do {} while (0)

/* ---- RCC ---- */
#define __HAL_RCC_GPIOA_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_GPIOB_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_GPIOC_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_GPIOF_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_SYSCFG_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_PWR_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_FDCAN_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_I2C1_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_USART2_CLK_ENABLE() do {} while (0)
#define __HAL_RCC_ADC12_CLK_ENABLE() do {} while (0)
#define RCC_FLAG_IWDGRST 1U
#define RCC_FLAG_WWDGRST 2U
#define RCC_FLAG_LPWRRST 3U
#define RCC_FLAG_SFTRST 4U
#define RCC_FLAG_OBLRST 5U
#define RCC_FLAG_BORRST 6U
#define RCC_FLAG_PINRST 7U
uint32_t stub_rcc_flag(uint32_t f);
#define __HAL_RCC_GET_FLAG(F) stub_rcc_flag(F)
#define __HAL_RCC_CLEAR_RESET_FLAGS() do {} while (0)
typedef struct { uint32_t PLLState, PLLSource, PLLM, PLLN, PLLP, PLLQ, PLLR; } RCC_PLLInitTypeDef;
typedef struct { uint32_t OscillatorType, HSEState, LSEState, HSIState, HSICalibrationValue, LSIState, HSI48State;
                 RCC_PLLInitTypeDef PLL; } RCC_OscInitTypeDef;
typedef struct { uint32_t ClockType, SYSCLKSource, AHBCLKDivider, APB1CLKDivider, APB2CLKDivider; } RCC_ClkInitTypeDef;
typedef struct { uint32_t PeriphClockSelection, Usart1ClockSelection, Usart2ClockSelection, I2c1ClockSelection,
                 FdcanClockSelection, Adc12ClockSelection; } RCC_PeriphCLKInitTypeDef;
#define RCC_OSCILLATORTYPE_HSE 1U
#define RCC_OSCILLATORTYPE_HSI 2U
#define RCC_HSE_ON 1U
#define RCC_HSE_OFF 0U
#define RCC_HSI_ON 1U
#define RCC_HSICALIBRATION_DEFAULT 0x40U
#define RCC_PLL_ON 2U
#define RCC_PLLSOURCE_HSE 3U
#define RCC_PLLSOURCE_HSI 2U
#define RCC_PLLM_DIV2 1U
#define RCC_PLLM_DIV4 3U
#define RCC_PLLP_DIV2 2U
#define RCC_PLLQ_DIV2 0U
#define RCC_PLLR_DIV2 0U
#define RCC_CLOCKTYPE_SYSCLK 1U
#define RCC_CLOCKTYPE_HCLK 2U
#define RCC_CLOCKTYPE_PCLK1 4U
#define RCC_CLOCKTYPE_PCLK2 8U
#define RCC_SYSCLKSOURCE_PLLCLK 3U
#define RCC_SYSCLK_DIV1 0U
#define RCC_HCLK_DIV1 0U
#define FLASH_LATENCY_4 4U
#define RCC_PERIPHCLK_USART2 2U
#define RCC_PERIPHCLK_I2C1 0x40U
#define RCC_PERIPHCLK_FDCAN 0x1000U
#define RCC_PERIPHCLK_ADC12 0x4000U
#define RCC_USART2CLKSOURCE_PCLK1 0U
#define RCC_I2C1CLKSOURCE_HSI 2U
#define RCC_FDCANCLKSOURCE_PCLK1 2U
#define RCC_ADC12CLKSOURCE_SYSCLK 2U
HAL_StatusTypeDef HAL_RCC_OscConfig(RCC_OscInitTypeDef *RCC_OscInitStruct);
HAL_StatusTypeDef HAL_RCC_ClockConfig(RCC_ClkInitTypeDef *RCC_ClkInitStruct, uint32_t FLatency);
HAL_StatusTypeDef HAL_RCCEx_PeriphCLKConfig(RCC_PeriphCLKInitTypeDef *PeriphClkInit);
void HAL_RCC_EnableCSS(void);
void HAL_RCC_NMI_IRQHandler(void);
void HAL_RCC_CSSCallback(void);

/* ---- PWR ---- */
#define PWR_REGULATOR_VOLTAGE_SCALE1_BOOST 0U
HAL_StatusTypeDef HAL_PWREx_ControlVoltageScaling(uint32_t VoltageScaling);
void HAL_PWREx_DisableUCPDDeadBattery(void);

/* ---- IWDG ---- */
typedef struct { uint32_t Prescaler, Reload, Window; } IWDG_InitTypeDef;
typedef struct { IWDG_TypeDef *Instance; IWDG_InitTypeDef Init; } IWDG_HandleTypeDef;
#define IWDG_PRESCALER_32 3U
#define IWDG_WINDOW_DISABLE 0x0FFFU
HAL_StatusTypeDef HAL_IWDG_Init(IWDG_HandleTypeDef *hiwdg);
HAL_StatusTypeDef HAL_IWDG_Refresh(IWDG_HandleTypeDef *hiwdg);

/* ---- I2C ---- */
typedef struct { uint32_t Timing, OwnAddress1, AddressingMode, DualAddressMode, OwnAddress2, OwnAddress2Masks,
                 GeneralCallMode, NoStretchMode; } I2C_InitTypeDef;
typedef struct { I2C_TypeDef *Instance; I2C_InitTypeDef Init; } I2C_HandleTypeDef;
#define I2C_ADDRESSINGMODE_7BIT 1U
#define I2C_DUALADDRESS_DISABLE 0U
#define I2C_OA2_NOMASK 0U
#define I2C_GENERALCALL_DISABLE 0U
#define I2C_NOSTRETCH_DISABLE 0U
#define I2C_ANALOGFILTER_ENABLE 0U
#define I2C_MEMADD_SIZE_8BIT 1U
HAL_StatusTypeDef HAL_I2C_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef HAL_I2CEx_ConfigAnalogFilter(I2C_HandleTypeDef *hi2c, uint32_t AnalogFilter);
HAL_StatusTypeDef HAL_I2CEx_ConfigDigitalFilter(I2C_HandleTypeDef *hi2c, uint32_t DigitalFilter);
HAL_StatusTypeDef HAL_I2C_Mem_Write(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint16_t MemAddress,
                                    uint16_t MemAddSize, uint8_t *pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_I2C_Mem_Read(I2C_HandleTypeDef *hi2c, uint16_t DevAddress, uint16_t MemAddress,
                                   uint16_t MemAddSize, uint8_t *pData, uint16_t Size, uint32_t Timeout);

/* ---- UART ---- */
typedef struct { uint32_t BaudRate, WordLength, StopBits, Parity, Mode, HwFlowCtl, OverSampling, OneBitSampling,
                 ClockPrescaler; } UART_InitTypeDef;
typedef struct { uint32_t AdvFeatureInit; } UART_AdvFeatureInitTypeDef;
typedef struct { USART_TypeDef *Instance; UART_InitTypeDef Init; UART_AdvFeatureInitTypeDef AdvancedInit; } UART_HandleTypeDef;
#define UART_WORDLENGTH_8B 0U
#define UART_STOPBITS_1 0U
#define UART_PARITY_NONE 0U
#define UART_MODE_TX_RX 0xCU
#define UART_HWCONTROL_NONE 0U
#define UART_OVERSAMPLING_16 0U
#define UART_ONE_BIT_SAMPLE_DISABLE 0U
#define UART_PRESCALER_DIV1 0U
#define UART_ADVFEATURE_NO_INIT 0U
HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef *huart);
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef *huart, const uint8_t *pData, uint16_t Size, uint32_t Timeout);

/* ---- ADC ---- */
typedef struct { uint32_t ClockPrescaler, Resolution, DataAlign, GainCompensation, ScanConvMode, EOCSelection;
                 FunctionalState LowPowerAutoWait, ContinuousConvMode; uint32_t NbrOfConversion;
                 FunctionalState DiscontinuousConvMode; uint32_t NbrOfDiscConversion, ExternalTrigConv,
                 ExternalTrigConvEdge, SamplingMode; FunctionalState DMAContinuousRequests; uint32_t Overrun;
                 FunctionalState OversamplingMode; } ADC_InitTypeDef;
typedef struct { ADC_TypeDef *Instance; ADC_InitTypeDef Init; } ADC_HandleTypeDef;
typedef struct { uint32_t Channel, Rank, SamplingTime, SingleDiff, OffsetNumber, Offset, OffsetSign;
                 FunctionalState OffsetSaturation; } ADC_ChannelConfTypeDef;
#define ADC_CLOCK_SYNC_PCLK_DIV4 3U
#define ADC_RESOLUTION_12B 0U
#define ADC_DATAALIGN_RIGHT 0U
#define ADC_SCAN_DISABLE 0U
#define ADC_EOC_SINGLE_CONV 4U
#define ADC_SOFTWARE_START 0U
#define ADC_EXTERNALTRIGCONVEDGE_NONE 0U
#define ADC_OVR_DATA_OVERWRITTEN 1U
#define ADC_SINGLE_ENDED 0x7FU
#define ADC_REGULAR_RANK_1 6U
#define ADC_SAMPLETIME_247CYCLES_5 6U
#define ADC_OFFSET_NONE 4U
#define ADC_CHANNEL_1 1U
#define ADC_CHANNEL_VREFINT 18U
#define ADC_CHANNEL_TEMPSENSOR_ADC1 16U
#define __HAL_ADC_CALC_VREFANALOG_VOLTAGE(D, R) ((3000UL * 1650UL) / (D))
#define __HAL_ADC_CALC_TEMPERATURE(V, D, R) ((int32_t)(D) - (int32_t)(V))
HAL_StatusTypeDef HAL_ADC_Init(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_ADCEx_Calibration_Start(ADC_HandleTypeDef *hadc, uint32_t SingleDiff);
HAL_StatusTypeDef HAL_ADC_ConfigChannel(ADC_HandleTypeDef *hadc, ADC_ChannelConfTypeDef *sConfig);
HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_ADC_Stop(ADC_HandleTypeDef *hadc);
HAL_StatusTypeDef HAL_ADC_PollForConversion(ADC_HandleTypeDef *hadc, uint32_t Timeout);
uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef *hadc);

/* ---- FDCAN ---- */
typedef struct { uint32_t ClockDivider, FrameFormat, Mode; FunctionalState AutoRetransmission, TransmitPause,
                 ProtocolException; uint32_t NominalPrescaler, NominalSyncJumpWidth, NominalTimeSeg1, NominalTimeSeg2,
                 DataPrescaler, DataSyncJumpWidth, DataTimeSeg1, DataTimeSeg2, StdFiltersNbr, ExtFiltersNbr,
                 TxFifoQueueMode; } FDCAN_InitTypeDef;
typedef struct { FDCAN_GlobalTypeDef *Instance; FDCAN_InitTypeDef Init; } FDCAN_HandleTypeDef;
typedef struct { uint32_t IdType, FilterIndex, FilterType, FilterConfig, FilterID1, FilterID2; } FDCAN_FilterTypeDef;
typedef struct { uint32_t Identifier, IdType, TxFrameType, DataLength, ErrorStateIndicator, BitRateSwitch, FDFormat,
                 TxEventFifoControl, MessageMarker; } FDCAN_TxHeaderTypeDef;
typedef struct { uint32_t Identifier, IdType, RxFrameType, DataLength, ErrorStateIndicator, BitRateSwitch, FDFormat,
                 RxTimestamp, FilterIndex, IsFilterMatchingFrame; } FDCAN_RxHeaderTypeDef;
typedef struct { uint32_t LastErrorCode, DataLastErrorCode, Activity, ErrorPassive, Warning, BusOff, RxESIflag,
                 RxBRSflag, RxFDFflag, ProtocolException, TDCvalue; } FDCAN_ProtocolStatusTypeDef;
typedef struct { uint32_t TxErrorCnt, RxErrorCnt, RxErrorPassive, ErrorLogging; } FDCAN_ErrorCountersTypeDef;
#define FDCAN_CLOCK_DIV1 0U
#define FDCAN_FRAME_CLASSIC 0U
#define FDCAN_MODE_NORMAL 0U
#define FDCAN_TX_FIFO_OPERATION 0U
#define FDCAN_STANDARD_ID 0U
#define FDCAN_FILTER_RANGE 0U
#define FDCAN_FILTER_DUAL 1U
#define FDCAN_FILTER_TO_RXFIFO0 1U
#define FDCAN_REJECT 2U
#define FDCAN_FILTER_REMOTE 0U
#define FDCAN_IT_RX_FIFO0_NEW_MESSAGE (1UL << 0)
#define FDCAN_IT_RX_FIFO0_MESSAGE_LOST (1UL << 2)
#define FDCAN_IT_ERROR_WARNING (1UL << 24)
#define FDCAN_IT_ERROR_PASSIVE (1UL << 23)
#define FDCAN_IT_BUS_OFF (1UL << 25)
#define FDCAN_DATA_FRAME 0U
#define FDCAN_DLC_BYTES_8 0x00080000U
#define FDCAN_ESI_ACTIVE 0U
#define FDCAN_BRS_OFF 0U
#define FDCAN_CLASSIC_CAN 0U
#define FDCAN_NO_TX_EVENTS 0U
#define FDCAN_RX_FIFO0 0x40U
#define FDCAN_PROTOCOL_ERROR_NO_CHANGE 7U
HAL_StatusTypeDef HAL_FDCAN_Init(FDCAN_HandleTypeDef *hfdcan);
HAL_StatusTypeDef HAL_FDCAN_ConfigFilter(FDCAN_HandleTypeDef *hfdcan, const FDCAN_FilterTypeDef *sFilterConfig);
HAL_StatusTypeDef HAL_FDCAN_ConfigGlobalFilter(FDCAN_HandleTypeDef *hfdcan, uint32_t NonMatchingStd,
                                               uint32_t NonMatchingExt, uint32_t RejectRemoteStd, uint32_t RejectRemoteExt);
HAL_StatusTypeDef HAL_FDCAN_ActivateNotification(FDCAN_HandleTypeDef *hfdcan, uint32_t ActiveITs, uint32_t BufferIndexes);
HAL_StatusTypeDef HAL_FDCAN_Start(FDCAN_HandleTypeDef *hfdcan);
HAL_StatusTypeDef HAL_FDCAN_AddMessageToTxFifoQ(FDCAN_HandleTypeDef *hfdcan, const FDCAN_TxHeaderTypeDef *pTxHeader,
                                                const uint8_t *pTxData);
HAL_StatusTypeDef HAL_FDCAN_GetRxMessage(FDCAN_HandleTypeDef *hfdcan, uint32_t RxLocation,
                                         FDCAN_RxHeaderTypeDef *pRxHeader, uint8_t *pRxData);
uint32_t HAL_FDCAN_GetTxFifoFreeLevel(const FDCAN_HandleTypeDef *hfdcan);
uint32_t HAL_FDCAN_GetRxFifoFillLevel(const FDCAN_HandleTypeDef *hfdcan, uint32_t RxFifo);
HAL_StatusTypeDef HAL_FDCAN_GetProtocolStatus(const FDCAN_HandleTypeDef *hfdcan, FDCAN_ProtocolStatusTypeDef *ProtocolStatus);
HAL_StatusTypeDef HAL_FDCAN_GetErrorCounters(const FDCAN_HandleTypeDef *hfdcan, FDCAN_ErrorCountersTypeDef *ErrorCounters);
void HAL_FDCAN_IRQHandler(FDCAN_HandleTypeDef *hfdcan);
void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef *hfdcan, uint32_t RxFifo0ITs);
void HAL_FDCAN_ErrorStatusCallback(FDCAN_HandleTypeDef *hfdcan, uint32_t ErrorStatusITs);
void HAL_FDCAN_MspInit(FDCAN_HandleTypeDef *hfdcan);
void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c);
void HAL_UART_MspInit(UART_HandleTypeDef *huart);
void HAL_ADC_MspInit(ADC_HandleTypeDef *hadc);
void HAL_MspInit(void);
#endif
