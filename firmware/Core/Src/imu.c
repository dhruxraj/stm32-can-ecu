/**
 * @file    imu.c
 * @brief   LSM6DS3TR-C driver: init, burst read, conversion, fault detection.
 */
#include "imu.h"

#include <string.h>

imu_t g_imu;

/* ---------------------------------------------------------------- pure part */
int16_t imu_accel_mg(int16_t raw)     /* 0.122 mg/LSB at +-4 g */
{
    return (int16_t)(((int32_t)raw * 122) / 1000);
}

int16_t imu_gyro_ddps(int16_t raw)    /* 17.50 mdps/LSB at 500 dps -> 0.175 x 0.1 dps */
{
    return (int16_t)(((int32_t)raw * 175) / 1000);
}

int16_t imu_temp_cdeg(int16_t raw)    /* 256 LSB/degC, 0 LSB = 25 degC */
{
    return (int16_t)(2500 + ((int32_t)raw * 100) / 256);
}

static int16_t le16(const uint8_t *p)
{
    return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

void imu_convert(const uint8_t b[14], imu_sample_t *s, int16_t raw6[6])
{
    /* b[0..1] temp, b[2..7] gyro X/Y/Z, b[8..13] accel X/Y/Z */
    int16_t t = le16(&b[0]);
    for (int i = 0; i < 3; i++) {
        raw6[i] = le16(&b[8 + 2 * i]);        /* accel */
        raw6[3 + i] = le16(&b[2 + 2 * i]);    /* gyro  */
    }
    s->ax_mg = imu_accel_mg(raw6[0]);
    s->ay_mg = imu_accel_mg(raw6[1]);
    s->az_mg = imu_accel_mg(raw6[2]);
    s->gx_ddps = imu_gyro_ddps(raw6[3]);
    s->gy_ddps = imu_gyro_ddps(raw6[4]);
    s->gz_ddps = imu_gyro_ddps(raw6[5]);
    s->temp_cdeg = imu_temp_cdeg(t);
}

bool imu_plausible(imu_t *imu, const int16_t raw[6])
{
    /* a real MEMS sensor always shows noise: 50 bit-identical samples in a
     * row (~1 s at 50 Hz) means the output registers are not updating */
    if (imu->have_last && memcmp(raw, imu->last_raw, sizeof imu->last_raw) == 0) {
        if (imu->stuck_count < 0xFFFFu) {
            imu->stuck_count++;
        }
    } else {
        imu->stuck_count = 0;
    }
    memcpy(imu->last_raw, raw, sizeof imu->last_raw);
    imu->have_last = true;
    bool all_zero_accel = (raw[0] == 0 && raw[1] == 0 && raw[2] == 0);
    return imu->stuck_count < IMU_STUCK_LIMIT && !all_zero_accel;
}

/* ---------------------------------------------------------------- HAL part */
#ifndef UNIT_TEST
#include "main.h"

#define IMU_ADDR   (IMU_I2C_ADDR_7BIT << 1)
#define IMU_TMO_MS 5u

static bool wr(uint8_t reg, uint8_t val)
{
    return HAL_I2C_Mem_Write(&hi2c1, IMU_ADDR, reg, I2C_MEMADD_SIZE_8BIT, &val, 1, IMU_TMO_MS) == HAL_OK;
}

static bool rd(uint8_t reg, uint8_t *buf, uint16_t n)
{
    return HAL_I2C_Mem_Read(&hi2c1, IMU_ADDR, reg, I2C_MEMADD_SIZE_8BIT, buf, n, IMU_TMO_MS) == HAL_OK;
}

bool imu_init(imu_t *imu, uint32_t now_ms)
{
    imu->last_init_ms = now_ms;
    imu->valid = false;
    imu->have_last = false;
    imu->stuck_count = 0;
    uint8_t id = 0;
    if (!rd(IMU_REG_WHO_AM_I, &id, 1)) {
        imu->i2c_errors++;
        imu->status = IMU_ST_COMM_FAULT;
        return false;
    }
    imu->who_am_i = id;
    if (id != IMU_WHO_AM_I_LSM6DS3TRC && id != IMU_WHO_AM_I_LSM6DSO) {
        imu->status = IMU_ST_COMM_FAULT;
        return false;
    }
    bool ok = wr(IMU_REG_CTRL3_C, IMU_CTRL3_SW_RESET);
    HAL_Delay(2);                                    /* SW reset takes ~50 us */
    ok = ok && wr(IMU_REG_CTRL3_C, IMU_CTRL3_BDU_INC);
    ok = ok && wr(IMU_REG_CTRL1_XL, IMU_CTRL1_104HZ_4G);
    ok = ok && wr(IMU_REG_CTRL2_G, IMU_CTRL2_104HZ_500);
    ok = ok && wr(IMU_REG_INT1_CTRL, IMU_INT1_DRDY_XL); /* INT1 (PB5) = accel data ready */
    uint8_t chk = 0;
    ok = ok && rd(IMU_REG_CTRL1_XL, &chk, 1) && chk == IMU_CTRL1_104HZ_4G;
    if (!ok) {
        imu->i2c_errors++;
        imu->status = IMU_ST_COMM_FAULT;
        return false;
    }
    imu->status = IMU_ST_OK;
    return true;
}

bool imu_read(imu_t *imu)
{
    uint8_t st = 0;
    uint8_t buf[14];
    if (!rd(IMU_REG_STATUS, &st, 1)) {
        imu->i2c_errors++;
        imu->status = IMU_ST_COMM_FAULT;
        imu->valid = false;
        return false;
    }
    if ((st & 0x03u) != 0x03u) {
        return imu->valid;          /* no new data yet - keep previous sample */
    }
    if (!rd(IMU_REG_OUT_TEMP_L, buf, sizeof buf)) {
        imu->i2c_errors++;
        imu->status = IMU_ST_COMM_FAULT;
        imu->valid = false;
        return false;
    }
    int16_t raw[6];
    imu_convert(buf, &imu->sample, raw);
    imu->reads++;
    if (imu_plausible(imu, raw)) {
        imu->status = IMU_ST_OK;
        imu->valid = true;
    } else {
        imu->status = IMU_ST_DATA_FAULT;
        imu->valid = false;
    }
    return imu->valid;
}

void imu_service(imu_t *imu, uint32_t now_ms)
{
    if (imu->status == IMU_ST_OK) {
        (void)imu_read(imu);
    } else if ((uint32_t)(now_ms - imu->last_init_ms) >= IMU_RETRY_MS) {
        /* comm or data fault: re-initialise once per second */
        (void)imu_init(imu, now_ms);
    }
}
#endif /* UNIT_TEST */
