#!/usr/bin/env bash
# Downloads the official STMicroelectronics STM32G4 HAL and CMSIS files
# (BSD-3-Clause / Apache-2.0) into firmware/Drivers.  Needs git + network.
# Alternatively copy the same folders from STM32CubeG4 (STM32CubeMX repository).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p Drivers/CMSIS/Device/ST
tmp=$(mktemp -d)
git clone --depth 1 https://github.com/STMicroelectronics/stm32g4xx_hal_driver.git "$tmp/hal"
git clone --depth 1 https://github.com/STMicroelectronics/cmsis_device_g4.git      "$tmp/dev"
git clone --depth 1 https://github.com/STMicroelectronics/cmsis_core.git           "$tmp/core"
rm -rf Drivers/STM32G4xx_HAL_Driver Drivers/CMSIS/Device/ST/STM32G4xx Drivers/CMSIS/Include
cp -r "$tmp/hal"  Drivers/STM32G4xx_HAL_Driver
cp -r "$tmp/dev"  Drivers/CMSIS/Device/ST/STM32G4xx
cp -r "$tmp/core/Include" Drivers/CMSIS/Include
rm -rf "$tmp"
echo "ST drivers installed in firmware/Drivers"
