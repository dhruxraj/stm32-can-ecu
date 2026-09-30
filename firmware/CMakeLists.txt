# STM32 CAN ECU firmware - STM32G431CBT6, STM32Cube HAL, arm-none-eabi-gcc
#   ./scripts/fetch_st_drivers.sh            (once: downloads HAL + CMSIS from ST's GitHub)
#   cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake -DCMAKE_BUILD_TYPE=Debug
#   cmake --build build                      -> build/can_ecu.elf / .hex / .bin
cmake_minimum_required(VERSION 3.20)
project(can_ecu C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(HAL   ${CMAKE_SOURCE_DIR}/Drivers/STM32G4xx_HAL_Driver)
set(CMSIS ${CMAKE_SOURCE_DIR}/Drivers/CMSIS)

if(NOT EXISTS ${HAL}/Src/stm32g4xx_hal.c)
  message(FATAL_ERROR "ST drivers missing - run scripts/fetch_st_drivers.sh first")
endif()

set(MCU_FLAGS -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard)

file(GLOB APP_SRC ${CMAKE_SOURCE_DIR}/Core/Src/*.c)
set(HAL_MODULES hal hal_adc hal_adc_ex hal_cortex hal_dma hal_dma_ex hal_exti hal_fdcan
    hal_flash hal_flash_ex hal_flash_ramfunc hal_gpio hal_i2c hal_i2c_ex hal_iwdg
    hal_pwr hal_pwr_ex hal_rcc hal_rcc_ex hal_uart hal_uart_ex ll_adc)
set(HAL_SRC)
foreach(m ${HAL_MODULES})
  list(APPEND HAL_SRC ${HAL}/Src/stm32g4xx_${m}.c)
endforeach()

add_executable(can_ecu
  ${APP_SRC} ${HAL_SRC}
  ${CMSIS}/Device/ST/STM32G4xx/Source/Templates/system_stm32g4xx.c
  ${CMSIS}/Device/ST/STM32G4xx/Source/Templates/gcc/startup_stm32g431xx.s)

target_compile_definitions(can_ecu PRIVATE USE_HAL_DRIVER STM32G431xx $<$<CONFIG:Debug>:DEBUG>)
target_include_directories(can_ecu PRIVATE
  ${CMAKE_SOURCE_DIR}/Core/Inc
  ${HAL}/Inc
  ${CMSIS}/Device/ST/STM32G4xx/Include
  ${CMSIS}/Include)
target_compile_options(can_ecu PRIVATE ${MCU_FLAGS} -Wall -Wextra -ffunction-sections -fdata-sections
  $<$<CONFIG:Debug>:-Og -g3> $<$<CONFIG:Release>:-O2 -g>)
set_source_files_properties(${HAL_SRC} PROPERTIES COMPILE_OPTIONS "-Wno-unused-parameter")
target_link_options(can_ecu PRIVATE ${MCU_FLAGS}
  -T${CMAKE_SOURCE_DIR}/STM32G431CBTX_FLASH.ld
  --specs=nano.specs --specs=nosys.specs
  -Wl,--gc-sections -Wl,-Map=${CMAKE_BINARY_DIR}/can_ecu.map -Wl,--print-memory-usage)

add_custom_command(TARGET can_ecu POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O ihex   $<TARGET_FILE:can_ecu> ${CMAKE_BINARY_DIR}/can_ecu.hex
  COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:can_ecu> ${CMAKE_BINARY_DIR}/can_ecu.bin
  COMMAND ${CMAKE_SIZE} $<TARGET_FILE:can_ecu>)
