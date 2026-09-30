/**
 * @file    board.h
 * @brief   Board pin map (rev A) and low-level board helpers.
 *          Must match hardware/gen/design.py and docs/PIN_MAPPING.md.
 */
#ifndef BOARD_H
#define BOARD_H

#include <stdbool.h>
#include <stdint.h>
#include "main.h"

/* LEDs: active high (MCU -> 680R -> LED -> GND) */
#define LED_STATUS_PORT   GPIOB
#define LED_STATUS_PIN    GPIO_PIN_12     /* green  D4 */
#define LED_FAULT_PORT    GPIOB
#define LED_FAULT_PIN     GPIO_PIN_13     /* red    D5 */
#define LED_CANTX_PORT    GPIOB
#define LED_CANTX_PIN     GPIO_PIN_14     /* yellow D6 */
#define LED_CANRX_PORT    GPIOB
#define LED_CANRX_PIN     GPIO_PIN_15     /* orange D7 */

/* USER button SW2: active low, 10k pull-up + 100 nF on board */
#define BTN_USER_PORT     GPIOC
#define BTN_USER_PIN      GPIO_PIN_13

/* CAN transceiver TJA1051T/3 pin 8 "S": HIGH = silent (10k pull-up), LOW = normal */
#define CAN_S_PORT        GPIOA
#define CAN_S_PIN         GPIO_PIN_8

/* Node ID solder jumpers to GND, internal pull-ups: closed = bit set */
#define NODE_ID0_PORT     GPIOB
#define NODE_ID0_PIN      GPIO_PIN_10     /* JP3 */
#define NODE_ID1_PORT     GPIOB
#define NODE_ID1_PIN      GPIO_PIN_11     /* JP4 */

/* IMU interrupt lines (inputs; firmware polls the status register) */
#define IMU_INT1_PORT     GPIOB
#define IMU_INT1_PIN      GPIO_PIN_5
#define IMU_INT2_PORT     GPIOB
#define IMU_INT2_PIN      GPIO_PIN_9

/* VIN sense: PA0 = ADC1_IN1, divider 100k / 15k -> ratio 7.667 */
#define VIN_DIV_NUM       115u
#define VIN_DIV_DEN       15u

typedef enum { LED_STATUS = 0, LED_FAULT, LED_CANTX, LED_CANRX, LED_COUNT } led_t;

void     board_gpio_init(void);
void     board_led(led_t led, bool on);
bool     board_button_pressed(void);
uint8_t  board_node_id(void);
void     board_can_transceiver_normal(bool normal);

bool     board_adc_init(void);
uint16_t board_vin_mv(void);        /* 0 on ADC error */
int16_t  board_mcu_temp_c(void);    /* INT16_MIN on ADC error */

#endif /* BOARD_H */
