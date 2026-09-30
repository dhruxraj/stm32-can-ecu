"""
canp.py - Python mirror of firmware/Core/Src/can_protocol.c
(IDs, payload decoding, rolling counter, CRC-8 SAE J1850).  No dependencies.
"""
import struct

BASE_ID, CMD_BASE_ID, CMD_BROADCAST_ID, MAX_NODES = 0x100, 0x0F0, 0x0FF, 4
MSG = {0: "HEARTBEAT", 1: "ACCEL", 2: "GYRO", 3: "BOARD", 4: "DIAG"}
STATE = {0: "INIT", 1: "RUN", 2: "DEGRADED", 3: "FAULT"}
CMD = {0: "NONE", 1: "IDENTIFY", 2: "CLEAR_FAULTS"}
RESET = {0: "UNKNOWN", 1: "POWER_ON", 2: "PIN", 3: "SOFTWARE", 4: "IWDG", 5: "WWDG", 6: "LOW_POWER", 7: "OPTION_BYTE"}
FAULTS = ["IMU_COMM", "IMU_DATA", "CAN_BUSOFF", "CAN_PASSIVE", "PEER_TIMEOUT", "CAN_E2E", "VIN_LOW", "VIN_HIGH",
          "HSE", "WDG_RESET", "CAN_TX_OVF", "MCU_TEMP", "ID_CONFLICT"]


def crc8_j1850(data):
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1D) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc ^ 0xFF


def frame_crc(can_id, d):
    return crc8_j1850(bytes([can_id & 0xFF, (can_id >> 8) & 0x07]) + bytes(d[:7]))


def msg_id(node, msg):
    return BASE_ID + ((node & 3) << 4) + msg


def cmd_id(target):
    return CMD_BROADCAST_ID if target == 0xFF else CMD_BASE_ID + (target & 3)


def decode_id(can_id):
    if CMD_BASE_ID <= can_id <= CMD_BASE_ID + 3 or can_id == CMD_BROADCAST_ID:
        return ("COMMAND", None if can_id == CMD_BROADCAST_ID else can_id - CMD_BASE_ID)
    off = can_id - BASE_ID
    if 0 <= off < MAX_NODES * 16 and (off & 0xF) in MSG:
        return (MSG[off & 0xF], off >> 4)
    return (None, None)


def seal(can_id, payload6, counter, status=0):
    d = bytearray(payload6[:6].ljust(6, b"\0"))
    d.append(((status & 0xF) << 4) | (counter & 0xF))
    d.append(frame_crc(can_id, d))
    return bytes(d)


def fault_names(mask):
    return [n for i, n in enumerate(FAULTS) if mask & (1 << i)] or ["none"]


def decode(can_id, data):
    """-> dict with 'msg', 'node', decoded signals, 'counter', 'status', 'crc_ok'."""
    kind, node = decode_id(can_id)
    if kind is None or len(data) != 8:
        return None
    d = bytes(data)
    out = {"msg": kind, "node": node, "counter": d[6] & 0xF, "status": d[6] >> 4,
           "crc_ok": frame_crc(can_id, d) == d[7]}
    if kind == "HEARTBEAT":
        out.update(node_id=d[0], state=STATE.get(d[1] & 3), faults=struct.unpack_from("<H", d, 2)[0],
                   peers=d[4], fw=f"{d[5] >> 4}.{d[5] & 15}")
    elif kind in ("ACCEL", "GYRO"):
        x, y, z = struct.unpack_from("<hhh", d, 0)
        k = 1.0 if kind == "ACCEL" else 0.1
        out.update(x=x * k, y=y * k, z=z * k, unit="mg" if kind == "ACCEL" else "dps")
    elif kind == "BOARD":
        v, t, up = struct.unpack_from("<HhH", d, 0)
        out.update(vin_v=v / 1000, imu_temp_c=t / 100, uptime_s=up)
    elif kind == "DIAG":
        out.update(tec=d[0], rec=d[1], proto_flags=d[2], busoff_count=d[3], e2e_errors=d[4],
                   reset_cause=RESET.get(d[5], d[5]))
    elif kind == "COMMAND":
        out.update(cmd=CMD.get(d[0], d[0]), source=d[1], arg=d[2])
    return out


class CounterCheck:
    """Rolling-counter supervision identical to canp_check() in the firmware."""
    def __init__(self):
        self.last = {}
        self.lost = 0
        self.repeats = 0

    def update(self, can_id, counter):
        prev = self.last.get(can_id)
        self.last[can_id] = counter
        if prev is None:
            return "ok"
        if counter == prev:
            self.repeats += 1
            return "repeat"
        exp = (prev + 1) & 0xF
        if counter != exp:
            self.lost += (counter - exp) & 0xF
            return "jump"
        return "ok"
