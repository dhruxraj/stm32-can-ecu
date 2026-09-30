#!/usr/bin/env python3
"""
can_monitor.py - live decoder for the STM32 CAN ECU bus.

Requires python-can (pip install python-can) and any adapter it supports, e.g.
  Linux SocketCAN : python3 can_monitor.py -i socketcan -c can0
  slcan (CANable) : python3 can_monitor.py -i slcan -c /dev/ttyACM0
  PEAK PCAN-USB   : python3 can_monitor.py -i pcan -c PCAN_USBBUS1
Bitrate 500 kbit/s (set it on the interface: `ip link set can0 type can bitrate 500000`).
Options: --raw  print every frame   --identify N  send IDENTIFY to node N (255 = all)
"""
import argparse
import time

from canp import decode, cmd_id, seal, CounterCheck, fault_names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--interface", default="socketcan")
    ap.add_argument("-c", "--channel", default="can0")
    ap.add_argument("-b", "--bitrate", type=int, default=500000)
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--identify", type=int, default=None, help="send IDENTIFY to node (255=all) and exit")
    ap.add_argument("--clear", type=int, default=None, help="send CLEAR_FAULTS to node (255=all) and exit")
    a = ap.parse_args()
    import can
    bus = can.Bus(interface=a.interface, channel=a.channel, bitrate=a.bitrate)
    if a.identify is not None or a.clear is not None:
        target = a.identify if a.identify is not None else a.clear
        code = 1 if a.identify is not None else 2
        cid = cmd_id(target)
        data = seal(cid, bytes([code, 0x0F, 0, 0, 0, 0]), counter=0)   # source 0x0F = PC tool
        bus.send(can.Message(arbitration_id=cid, data=data, is_extended_id=False))
        print(f"sent {'IDENTIFY' if code == 1 else 'CLEAR_FAULTS'} to 0x{cid:03X}: {data.hex(' ')}")
        return
    cc = CounterCheck()
    stats = {"frames": 0, "crc_err": 0}
    last_print = 0.0
    latest = {}
    print("listening ... Ctrl+C to stop")
    try:
        while True:
            m = bus.recv(0.2)
            now = time.time()
            if m is not None and not m.is_extended_id and not m.is_remote_frame:
                stats["frames"] += 1
                r = decode(m.arbitration_id, m.data)
                if r is None:
                    if a.raw:
                        print(f"  unknown 0x{m.arbitration_id:03X} {bytes(m.data).hex(' ')}")
                    continue
                if not r["crc_ok"]:
                    stats["crc_err"] += 1
                r["seq"] = cc.update(m.arbitration_id, r["counter"])
                latest[(r["msg"], r["node"])] = r
                if a.raw:
                    print(f"0x{m.arbitration_id:03X} {bytes(m.data).hex(' ')}  {r}")
            if now - last_print > 1.0 and not a.raw:
                last_print = now
                print(f"\n--- {time.strftime('%H:%M:%S')}  frames {stats['frames']}  CRC errors {stats['crc_err']}  "
                      f"lost {cc.lost}  repeats {cc.repeats}")
                for node in range(4):
                    hb = latest.get(("HEARTBEAT", node))
                    if not hb:
                        continue
                    ac = latest.get(("ACCEL", node), {})
                    gy = latest.get(("GYRO", node), {})
                    bd = latest.get(("BOARD", node), {})
                    dg = latest.get(("DIAG", node), {})
                    print(f"node {node}: {hb['state']:<8} faults {fault_names(hb['faults'])} peers 0x{hb['peers']:X} fw {hb['fw']}")
                    if ac:
                        print(f"   accel {ac['x']:7.0f} {ac['y']:7.0f} {ac['z']:7.0f} mg   "
                              f"gyro {gy.get('x', 0):7.1f} {gy.get('y', 0):7.1f} {gy.get('z', 0):7.1f} dps")
                    if bd:
                        print(f"   VIN {bd['vin_v']:.2f} V  IMU {bd['imu_temp_c']:.1f} C  uptime {bd['uptime_s']} s")
                    if dg:
                        print(f"   TEC {dg['tec']} REC {dg['rec']} bus-off {dg['busoff_count']} "
                              f"E2E err {dg['e2e_errors']} reset {dg['reset_cause']}")
    except KeyboardInterrupt:
        pass
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
