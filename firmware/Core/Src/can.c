/**
 * @file    can.c
 * @brief   FDCAN1 (PA11 = RX, PA12 = TX, AF9) + TJA1051T/3 transceiver.
 *
 * Bit timing (FDCAN kernel clock = PCLK1 = 170 MHz, see HAL_FDCAN_MspInit):
 *   prescaler 17 -> tq = 100 ns, 1 + 15 + 4 = 20 tq = 2.0 us -> 500 kbit/s,
 *   sample point 80 %, SJW 4 tq.
 */
#include "can.h"

#include <string.h>
#include "board.h"
#include "can_protocol.h"
#include "main.h"

FDCAN_HandleTypeDef hfdcan1;

static can_frame_t        s_rxq[CAN_RX_QUEUE_LEN];
static volatile uint32_t  s_rx_head;       /* written by ISR  */
static volatile uint32_t  s_rx_tail;       /* written by main */
static volatile bool      s_busoff_irq;
static uint32_t           s_busoff_since;
static bool               s_busoff_pending;
static can_status_t       s_st;

static uint8_t dlc_to_len(uint32_t dl)
{
    /* HAL versions differ: DataLength is either the DLC code (0..15) or the
     * code shifted left by 16 (FDCAN_DLC_BYTES_x). Handle both. */
    if (dl > 0xFu) {
        dl >>= 16;
    }
    return (uint8_t)(dl > 8u ? 8u : dl);
}

bool can_init(uint8_t node_id)
{
    hfdcan1.Instance = FDCAN1;
    hfdcan1.Init.ClockDivider = FDCAN_CLOCK_DIV1;
    hfdcan1.Init.FrameFormat = FDCAN_FRAME_CLASSIC;
    hfdcan1.Init.Mode = FDCAN_MODE_NORMAL;
    hfdcan1.Init.AutoRetransmission = ENABLE;
    hfdcan1.Init.TransmitPause = DISABLE;
    hfdcan1.Init.ProtocolException = DISABLE;
    hfdcan1.Init.NominalPrescaler = 17;
    hfdcan1.Init.NominalSyncJumpWidth = 4;
    hfdcan1.Init.NominalTimeSeg1 = 15;
    hfdcan1.Init.NominalTimeSeg2 = 4;
    hfdcan1.Init.DataPrescaler = 17;          /* unused for classic frames */
    hfdcan1.Init.DataSyncJumpWidth = 4;
    hfdcan1.Init.DataTimeSeg1 = 15;
    hfdcan1.Init.DataTimeSeg2 = 4;
    hfdcan1.Init.StdFiltersNbr = 2;
    hfdcan1.Init.ExtFiltersNbr = 0;
    hfdcan1.Init.TxFifoQueueMode = FDCAN_TX_FIFO_OPERATION;
    if (HAL_FDCAN_Init(&hfdcan1) != HAL_OK) {
        return false;
    }

    FDCAN_FilterTypeDef f = {0};
    /* filter 0: all ECU data frames 0x100..0x13F (4 nodes x 16 messages) */
    f.IdType = FDCAN_STANDARD_ID;
    f.FilterIndex = 0;
    f.FilterType = FDCAN_FILTER_RANGE;
    f.FilterConfig = FDCAN_FILTER_TO_RXFIFO0;
    f.FilterID1 = CANP_BASE_ID;
    f.FilterID2 = CANP_BASE_ID + (CANP_MAX_NODES << 4) - 1u;
    if (HAL_FDCAN_ConfigFilter(&hfdcan1, &f) != HAL_OK) return false;
    /* filter 1: commands addressed to this node + broadcast command */
    f.FilterIndex = 1;
    f.FilterType = FDCAN_FILTER_DUAL;
    f.FilterID1 = canp_cmd_id(node_id);
    f.FilterID2 = CANP_CMD_BROADCAST_ID;
    if (HAL_FDCAN_ConfigFilter(&hfdcan1, &f) != HAL_OK) return false;
    /* everything else (other IDs, extended IDs, remote frames) is rejected */
    if (HAL_FDCAN_ConfigGlobalFilter(&hfdcan1, FDCAN_REJECT, FDCAN_REJECT,
                                     FDCAN_FILTER_REMOTE, FDCAN_FILTER_REMOTE) != HAL_OK) return false;

    if (HAL_FDCAN_ActivateNotification(&hfdcan1,
            FDCAN_IT_RX_FIFO0_NEW_MESSAGE | FDCAN_IT_RX_FIFO0_MESSAGE_LOST |
            FDCAN_IT_BUS_OFF | FDCAN_IT_ERROR_PASSIVE | FDCAN_IT_ERROR_WARNING, 0) != HAL_OK) return false;
    if (HAL_FDCAN_Start(&hfdcan1) != HAL_OK) return false;

    board_can_transceiver_normal(true);        /* S = LOW: leave silent mode */
    return true;
}

bool can_send(uint16_t id, const uint8_t data[8])
{
    FDCAN_TxHeaderTypeDef h = {0};
    h.Identifier = id;
    h.IdType = FDCAN_STANDARD_ID;
    h.TxFrameType = FDCAN_DATA_FRAME;
    h.DataLength = FDCAN_DLC_BYTES_8;
    h.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    h.BitRateSwitch = FDCAN_BRS_OFF;
    h.FDFormat = FDCAN_CLASSIC_CAN;
    h.TxEventFifoControl = FDCAN_NO_TX_EVENTS;
    h.MessageMarker = 0;
    if (s_st.busoff || HAL_FDCAN_GetTxFifoFreeLevel(&hfdcan1) == 0u) {
        s_st.tx_fail++;
        return false;
    }
    if (HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan1, &h, (uint8_t *)data) != HAL_OK) {
        s_st.tx_fail++;
        return false;
    }
    s_st.tx_ok++;
    return true;
}

bool can_receive(can_frame_t *f)
{
    uint32_t tail = s_rx_tail;
    if (tail == s_rx_head) {
        return false;
    }
    *f = s_rxq[tail & (CAN_RX_QUEUE_LEN - 1u)];
    __DMB();
    s_rx_tail = tail + 1u;
    return true;
}

void can_poll(uint32_t now_ms)
{
    FDCAN_ProtocolStatusTypeDef ps;
    FDCAN_ErrorCountersTypeDef ec;
    if (HAL_FDCAN_GetProtocolStatus(&hfdcan1, &ps) == HAL_OK) {
        s_st.warning = ps.Warning != 0u;
        s_st.passive = ps.ErrorPassive != 0u;
        s_st.busoff = ps.BusOff != 0u;
        if (ps.LastErrorCode != FDCAN_PROTOCOL_ERROR_NO_CHANGE) {
            s_st.lec = (uint8_t)(ps.LastErrorCode & 0x7u);
        }
    }
    if (HAL_FDCAN_GetErrorCounters(&hfdcan1, &ec) == HAL_OK) {
        s_st.tec = (uint8_t)ec.TxErrorCnt;
        s_st.rec = (uint8_t)ec.RxErrorCnt;
    }
    if (s_busoff_irq) {
        s_busoff_irq = false;
        s_busoff_pending = true;
        s_busoff_since = now_ms;
        s_st.busoff_events++;
    }
    /* Bus-off: hardware sets CCCR.INIT. After a short wait, clear INIT; the
     * controller then waits for 128 x 11 recessive bits before rejoining. */
    if (s_busoff_pending && (uint32_t)(now_ms - s_busoff_since) >= CAN_BUSOFF_WAIT_MS) {
        CLEAR_BIT(hfdcan1.Instance->CCCR, FDCAN_CCCR_INIT);
        s_busoff_pending = false;
    }
}

void can_get_status(can_status_t *s)
{
    *s = s_st;
}

/* ------------------------------------------------------------ HAL callbacks */
void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef *hfdcan, uint32_t RxFifo0ITs)
{
    if (RxFifo0ITs & FDCAN_IT_RX_FIFO0_MESSAGE_LOST) {
        s_st.rx_overflow++;
    }
    if ((RxFifo0ITs & FDCAN_IT_RX_FIFO0_NEW_MESSAGE) == 0u) {
        return;
    }
    FDCAN_RxHeaderTypeDef h;
    uint8_t d[8];
    while (HAL_FDCAN_GetRxFifoFillLevel(hfdcan, FDCAN_RX_FIFO0) > 0u) {
        if (HAL_FDCAN_GetRxMessage(hfdcan, FDCAN_RX_FIFO0, &h, d) != HAL_OK) {
            break;
        }
        if (h.IdType != FDCAN_STANDARD_ID || h.RxFrameType != FDCAN_DATA_FRAME) {
            continue;
        }
        uint32_t head = s_rx_head;
        if ((uint32_t)(head - s_rx_tail) >= CAN_RX_QUEUE_LEN) {
            s_st.rx_overflow++;               /* software queue full: drop */
            continue;
        }
        can_frame_t *f = &s_rxq[head & (CAN_RX_QUEUE_LEN - 1u)];
        f->id = (uint16_t)h.Identifier;
        f->dlc = dlc_to_len(h.DataLength);
        memcpy(f->data, d, 8);
        f->ts_ms = HAL_GetTick();
        __DMB();
        s_rx_head = head + 1u;
        s_st.rx_ok++;
    }
}

void HAL_FDCAN_ErrorStatusCallback(FDCAN_HandleTypeDef *hfdcan, uint32_t ErrorStatusITs)
{
    (void)hfdcan;
    if (ErrorStatusITs & FDCAN_IT_BUS_OFF) {
        s_busoff_irq = true;
    }
}
