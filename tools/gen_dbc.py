#!/usr/bin/env python3
"""Generates can_ecu.dbc (all 4 node IDs + commands) from the protocol definition."""
MSGS = {
    0: ("Heartbeat", 100, [("NodeId", 0, 8, False, 1, 0, 0, 3, ""), ("State", 8, 8, False, 1, 0, 0, 3, ""),
                           ("Faults", 16, 16, False, 1, 0, 0, 65535, ""), ("PeersAlive", 32, 8, False, 1, 0, 0, 15, ""),
                           ("FwVersion", 40, 8, False, 1, 0, 0, 255, "")]),
    1: ("Accel", 20, [("AccX", 0, 16, True, 1, 0, -4000, 4000, "mg"), ("AccY", 16, 16, True, 1, 0, -4000, 4000, "mg"),
                      ("AccZ", 32, 16, True, 1, 0, -4000, 4000, "mg")]),
    2: ("Gyro", 20, [("GyroX", 0, 16, True, 0.1, 0, -500, 500, "deg/s"), ("GyroY", 16, 16, True, 0.1, 0, -500, 500, "deg/s"),
                     ("GyroZ", 32, 16, True, 0.1, 0, -500, 500, "deg/s")]),
    3: ("Board", 100, [("Vin", 0, 16, False, 0.001, 0, 0, 30, "V"), ("ImuTemp", 16, 16, True, 0.01, 0, -40, 125, "degC"),
                       ("Uptime", 32, 16, False, 1, 0, 0, 65535, "s")]),
    4: ("Diag", 1000, [("TEC", 0, 8, False, 1, 0, 0, 255, ""), ("REC", 8, 8, False, 1, 0, 0, 255, ""),
                       ("ProtoFlags", 16, 8, False, 1, 0, 0, 255, ""), ("BusOffCount", 24, 8, False, 1, 0, 0, 255, ""),
                       ("E2EErrors", 32, 8, False, 1, 0, 0, 255, ""), ("ResetCause", 40, 8, False, 1, 0, 0, 7, "")]),
}
TAIL = [("Counter", 48, 4, False, 1, 0, 0, 15, ""), ("Status", 52, 4, False, 1, 0, 0, 15, ""),
        ("CRC", 56, 8, False, 1, 0, 0, 255, "")]


def sg(name, start, ln, signed, f, o, lo, hi, unit, rx="Vector__XXX"):
    fs = f"{f:g}"
    return f' SG_ {name} : {start}|{ln}@1{"-" if signed else "+"} ({fs},{o}) [{lo}|{hi}] "{unit}" {rx}'


def main(path="can_ecu.dbc"):
    L = ['VERSION "STM32 CAN ECU rev A protocol 1.0"', "", "NS_ :", "\tCM_", "\tBA_DEF_", "\tBA_", "\tVAL_",
         "\tBA_DEF_DEF_", "", "BS_:", "", "BU_: ECU0 ECU1 ECU2 ECU3 PC_TOOL", ""]
    cms, vals, cycles = [], [], []
    for node in range(4):
        for mid, (name, period, sigs) in MSGS.items():
            cid = 0x100 + (node << 4) + mid
            L.append(f"BO_ {cid} {name}_N{node}: 8 ECU{node}")
            for s in sigs + TAIL:
                L.append(sg(*s))
            L.append("")
            cycles.append(f'BA_ "GenMsgCycleTime" BO_ {cid} {period};')
            if mid == 0:
                vals.append(f'VAL_ {cid} State 0 "INIT" 1 "RUN" 2 "DEGRADED" 3 "FAULT" ;')
            if mid == 4:
                vals.append(f'VAL_ {cid} ResetCause 0 "UNKNOWN" 1 "POWER_ON" 2 "PIN" 3 "SOFTWARE" 4 "IWDG" '
                            f'5 "WWDG" 6 "LOW_POWER" 7 "OPTION_BYTE" ;')
    for cid, name in [(0x0F0, "Cmd_N0"), (0x0F1, "Cmd_N1"), (0x0F2, "Cmd_N2"), (0x0F3, "Cmd_N3"), (0x0FF, "Cmd_All")]:
        L.append(f"BO_ {cid} {name}: 8 PC_TOOL")
        for s in [("Command", 0, 8, False, 1, 0, 0, 2, ""), ("SourceNode", 8, 8, False, 1, 0, 0, 255, ""),
                  ("Arg", 16, 8, False, 1, 0, 0, 255, "")] + TAIL:
            L.append(sg(*s))
        L.append("")
        vals.append(f'VAL_ {cid} Command 0 "NONE" 1 "IDENTIFY" 2 "CLEAR_FAULTS" ;')
    cms.append('CM_ "Byte 6: Counter (bits 0-3) + Status nibble (bits 4-7). Byte 7: CRC-8 SAE J1850 '
               '(poly 0x1D, init 0xFF, xorout 0xFF) over [ID low byte, ID high byte, byte 0..6]. '
               'E2E-inspired, not AUTOSAR compliant.";')
    L += cms + ['BA_DEF_ BO_ "GenMsgCycleTime" INT 0 65535;', 'BA_DEF_DEF_ "GenMsgCycleTime" 0;'] + cycles + vals
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
