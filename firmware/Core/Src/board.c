/**
 * @file    board.c
 * @brief   GPIO configuration, LEDs, button, node ID, ADC measurements.
 */
#include "board.h"

ADC_HandleTypeDef hadc1;

static const struct { GPIO_TypeDef *port; uint16_t pin; } s_led[LED_COUNT] = {
    { LED_STATUS_PORT, LED_STATUS_PIN }, { LED_FAULT_PORT, LED_FAULT_PIN },
    { LED_CANTX_PORT, LED_CANTX_PIN },   { LED_CANRX_PORT, LED_CANRX_PIN },
};

void board_gpio_init(void)
{
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();

    /* outputs: safe levels first */
    HAL_GPIO_WritePin(GPIOB, LED_STATUS_PIN | LED_FAULT_PIN | LED_CANTX_PIN | LED_CANRX_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CAN_S_PORT, CAN_S_PIN, GPIO_PIN_SET);          /* transceiver silent */

    g.Pin = LED_STATUS_PIN | LED_FAULT_PIN | LED_CANTX_PIN | LED_CANRX_PIN;
    g.Mode = GPIO_MODE_OUTPUT_PP;
    g.Pull = GPIO_NOPULL;
    g.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOB, &g);

    g.Pin = CAN_S_PIN;
    HAL_GPIO_Init(CAN_S_PORT, &g);

    g.Pin = BTN_USER_PIN;
    g.Mode = GPIO_MODE_INPUT;
    g.Pull = GPIO_NOPULL;                                             /* external 10k */
    HAL_GPIO_Init(BTN_USER_PORT, &g);

    g.Pin = NODE_ID0_PIN | NODE_ID1_PIN;
    g.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOB, &g);

    g.Pin = IMU_INT1_PIN | IMU_INT2_PIN;
    g.Pull = GPIO_PULLDOWN;                                           /* IMU INT is push-pull */
    HAL_GPIO_Init(GPIOB, &g);

    /* unused / not-connected pins -> analog (lowest power, no floating inputs).
     * Expansion header pins PA4..PA7, PB0 are also left analog until used.   */
    g.Mode = GPIO_MODE_ANALOG;
    g.Pull = GPIO_NOPULL;
    g.Pin = GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_7 | GPIO_PIN_9 | GPIO_PIN_10;
    HAL_GPIO_Init(GPIOA, &g);
    g.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_4 | GPIO_PIN_6;
    HAL_GPIO_Init(GPIOB, &g);
    g.Pin = GPIO_PIN_14 | GPIO_PIN_15;
    HAL_GPIO_Init(GPIOC, &g);
}

void board_led(led_t led, bool on)
{
    if (led < LED_COUNT) {
        HAL_GPIO_WritePin(s_led[led].port, s_led[led].pin, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
    }
}

bool board_button_pressed(void)
{
    return HAL_GPIO_ReadPin(BTN_USER_PORT, BTN_USER_PIN) == GPIO_PIN_RESET;
}

uint8_t board_node_id(void)
{
    uint8_t id = 0;
    if (HAL_GPIO_ReadPin(NODE_ID0_PORT, NODE_ID0_PIN) == GPIO_PIN_RESET) id |= 1u;
    if (HAL_GPIO_ReadPin(NODE_ID1_PORT, NODE_ID1_PIN) == GPIO_PIN_RESET) id |= 2u;
    return id;
}

void board_can_transceiver_normal(bool normal)
{
    HAL_GPIO_WritePin(CAN_S_PORT, CAN_S_PIN, normal ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

/* ------------------------------------------------------------------ ADC */
bool board_adc_init(void)
{
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;     /* 170/4 = 42.5 MHz */
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.GainCompensation = 0;
    hadc1.Init.ScanConvMode = ADC_SCAN_DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    hadc1.Init.LowPowerAutoWait = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
    hadc1.Init.OversamplingMode = DISABLE;
    if (HAL_ADC_Init(&hadc1) != HAL_OK) {
        return false;
    }
    return HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED) == HAL_OK;
}

static bool adc_read(uint32_t channel, uint32_t *raw)
{
    ADC_ChannelConfTypeDef c = {0};
    c.Channel = channel;
    c.Rank = ADC_REGULAR_RANK_1;
    c.SamplingTime = ADC_SAMPLETIME_247CYCLES_5;              /* >5 us for VREFINT/TS */
    c.SingleDiff = ADC_SINGLE_ENDED;
    c.OffsetNumber = ADC_OFFSET_NONE;
    c.Offset = 0;
    if (HAL_ADC_ConfigChannel(&hadc1, &c) != HAL_OK) return false;
    if (HAL_ADC_Start(&hadc1) != HAL_OK) return false;
    if (HAL_ADC_PollForConversion(&hadc1, 2) != HAL_OK) {
        (void)HAL_ADC_Stop(&hadc1);
        return false;
    }
    *raw = HAL_ADC_GetValue(&hadc1);
    (void)HAL_ADC_Stop(&hadc1);
    return true;
}

static uint32_t vdda_mv(void)
{
    uint32_t vref = 0;
    if (!adc_read(ADC_CHANNEL_VREFINT, &vref) || vref == 0u) {
        return 3300u;                                       /* nominal fallback */
    }
    return __HAL_ADC_CALC_VREFANALOG_VOLTAGE(vref, ADC_RESOLUTION_12B);
}

uint16_t board_vin_mv(void)
{
    uint32_t raw = 0;
    uint32_t vdda = vdda_mv();
    if (!adc_read(ADC_CHANNEL_1, &raw)) {
        return 0u;
    }
    uint32_t pin_mv = (raw * vdda) / 4095u;
    return (uint16_t)((pin_mv * VIN_DIV_NUM) / VIN_DIV_DEN);
}

int16_t board_mcu_temp_c(void)
{
    uint32_t raw = 0;
    uint32_t vdda = vdda_mv();
    if (!adc_read(ADC_CHANNEL_TEMPSENSOR_ADC1, &raw)) {
        return INT16_MIN;
    }
    return (int16_t)__HAL_ADC_CALC_TEMPERATURE(vdda, raw, ADC_RESOLUTION_12B);
}
