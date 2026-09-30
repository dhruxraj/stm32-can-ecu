#!/usr/bin/env python3
"""Cross-checks the Python protocol implementation against the C firmware
(golden vectors printed by firmware/tests/test_runner) and the DBC file."""
import re
from canp import crc8_j1850, decode, seal, msg_id, cmd_id

ok = 0
def check(c, msg):
    global ok
    assert c, msg
    ok += 1

check(crc8_j1850(b"123456789") == 0x4B, "CRC-8/SAE-J1850 check value")
# golden vectors from the C unit test (VECTOR lines)
v1 = bytes.fromhex("01 01 00 00 01 10 03 3A")
v2 = bytes.fromhex("0C 00 DD FF E6 03 17 7E")
check(seal(0x110, bytes([1, 1, 0, 0, 1, 0x10]), 3, 0) == v1, "heartbeat vector == C")
check(seal(0x101, bytes.fromhex("0C00DDFFE603"), 7, 1) == v2, "accel vector == C")
r = decode(0x101, v2)
check(r["crc_ok"] and r["msg"] == "ACCEL" and r["node"] == 0 and (r["x"], r["y"], r["z"]) == (12, -35, 998), "decode accel")
r = decode(0x110, v1)
check(r["state"] == "RUN" and r["node"] == 1 and r["fw"] == "1.0", "decode heartbeat")
check(not decode(0x110, bytes([1, 1, 0, 0, 1, 0x10, 3, 0x3B]))["crc_ok"], "corrupt CRC detected")
check(msg_id(3, 4) == 0x134 and cmd_id(255) == 0x0FF and cmd_id(1) == 0x0F1, "ids")
# DBC sanity: every BO_ has 8-byte DLC, every signal fits in 64 bits, no overlaps
dbc = open("can_ecu.dbc").read()
msgs = re.findall(r"BO_ (\d+) (\w+): 8 \w+\n((?: SG_ .*\n)+)", dbc)
check(len(msgs) == 25, f"25 messages in DBC (got {len(msgs)})")
for cid, name, body in msgs:
    used = 0
    for s, ln in re.findall(r"SG_ \w+ : (\d+)\|(\d+)@1", body):
        mask = ((1 << int(ln)) - 1) << int(s)
        check(mask < (1 << 64) and not (used & mask), f"signal layout {name}")
        used |= mask
print(f"tools self-test: {ok} checks passed")
