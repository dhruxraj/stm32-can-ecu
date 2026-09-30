# Host unit tests (gcc/clang on Linux/macOS/WSL) + HAL-stub compile check
CC ?= gcc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -O1 -g -DUNIT_TEST -I../Core/Inc
SRC = ../Core/Src/can_protocol.c ../Core/Src/diagnostics.c ../Core/Src/imu.c

all: test stubcheck

test: test_main.c $(SRC)
	$(CC) $(CFLAGS) -fsanitize=address,undefined -o test_runner test_main.c $(SRC)
	./test_runner

# Compiles EVERY firmware source against minimal HAL stubs (hal_stub/) with
# warnings as errors. This catches syntax/type errors on a PC without the ST
# HAL; it does NOT replace a real arm-none-eabi build against the ST HAL.
stubcheck:
	@for f in ../Core/Src/*.c; do \
	  $(CC) -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -fsyntax-only \
	    -DSTM32G431xx -DUSE_HAL_DRIVER -Ihal_stub -I../Core/Inc $$f || exit 1; \
	  echo "  stub-compiled $$f"; done

clean:
	rm -f test_runner
.PHONY: all test stubcheck clean
