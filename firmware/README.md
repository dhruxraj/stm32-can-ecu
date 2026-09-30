# STM32 CAN ECU firmware

STM32G431CBT6 · STM32Cube HAL · C11 · no RTOS. Full documentation is in [`../docs/FIRMWARE.md`](../docs/FIRMWARE.md). The CAN protocol is described in [`../docs/CAN_PROTOCOL.md`](../docs/CAN_PROTOCOL.md).

```bash
./scripts/fetch_st_drivers.sh
cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake -DCMAKE_BUILD_TYPE=Debug
cmake --build build
STM32_Programmer_CLI -c port=SWD mode=UR -w build/can_ecu.hex -v -rst
make -C tests            # host unit tests
```
