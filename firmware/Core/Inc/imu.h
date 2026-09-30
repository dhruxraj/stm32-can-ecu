/**
 * @file    imu.h
 * @brief   LSM6DS3TR-C 6-axis IMU driver (I2C1, address 0x6A).
 *          Configuration: accel +-4 g, gyro +-500 dps, both 104 Hz, BDU on.
 *          LSM6DSO (WHO_AM_I 0x6C) is accepted as a register-compatible
 *          alternative for the registers used here.
 */
#ifndef IMU_H
#define IMU_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define IMU_I2C_ADDR_7BIT        0x6Au    /* SDO/SA0 tied to GND */
#define IMU_WHO_AM_I_LSM6DS3TRC  0x6Au
#define IMU_WHO_AM_I_LSM6DSO     0x6Cu

/* registers (LSM6DS3TR-C datasheet, register map) */
#define IMU_REG_INT1_CTRL   0x0Du
#define IMU_REG_WHO_AM_I    0x0Fu
#define IMU_REG_CTRL1_XL    0x10u
#define IMU_REG_CTRL2_G     0x11u
#define IMU_REG_CTRL3_C     0x12u
#define IMU_REG_STATUS      0x1Eu
#define IMU_REG_OUT_TEMP_L  0x20u     /* 0x20..0x2D: temp, gyro XYZ, accel XYZ */

#define IMU_CTRL3_SW_RESET  0x01u
#define IMU_CTRL3_BDU_INC   0x44u     /* BDU=1, IF_INC=1 */
#define IMU_CTRL1_104HZ_4G  0x48u     /* ODR_XL=0100 (104 Hz), FS_XL=10 (+-4 g) */
#define IMU_CTRL2_104HZ_500 0x44u     /* ODR_G=0100 (104 Hz), FS_G=01 (500 dps) */
#define IMU_INT1_DRDY_XL    0x01u

#define IMU_STUCK_LIMIT     50u       /* identical samples in a row -> data fault */
#define IMU_RETRY_MS        1000u

typedef enum { IMU_ST_UNINIT = 0, IMU_ST_OK, IMU_ST_COMM_FAULT, IMU_ST_DATA_FAULT } imu_status_t;

typedef struct {
    int16_t ax_mg, ay_mg, az_mg;        /* milli-g            */
    int16_t gx_ddps, gy_ddps, gz_ddps;  /* 0.1 deg/s          */
    int16_t temp_cdeg;                  /* 0.01 degC          */
} imu_sample_t;

typedef struct {
    imu_status_t status;
    uint8_t      who_am_i;
    uint32_t     i2c_errors;
    uint32_t     reads;
    uint16_t     stuck_count;
    int16_t      last_raw[6];
    bool         have_last;
    bool         valid;                 /* sample contains fresh, plausible data */
    imu_sample_t sample;
    uint32_t     last_init_ms;
} imu_t;

extern imu_t g_imu;

/* pure conversion / plausibility helpers (host tested) */
int16_t imu_accel_mg(int16_t raw);
int16_t imu_gyro_ddps(int16_t raw);
int16_t imu_temp_cdeg(int16_t raw);
bool    imu_plausible(imu_t *imu, const int16_t raw[6]);
void    imu_convert(const uint8_t buf[14], imu_sample_t *s, int16_t raw6[6]);

/* hardware functions (imu.c, need HAL) */
bool imu_init(imu_t *imu, uint32_t now_ms);
bool imu_read(imu_t *imu);
void imu_service(imu_t *imu, uint32_t now_ms);   /* read or retry init */

#ifdef __cplusplus
}
#endif
#endif /* IMU_H */
