#!/usr/bin/env python3
"""
dvfs_sim_controller.py
User-space simulation of DVFS + core parking controller.
No /sys writes — safe on VMs and servers without cpufreq.
Outputs CSV with decisions and estimated power samples.

Run:
  sudo python3 dvfs_sim_controller.py --out /tmp/dvfs_log.csv --duration 120
"""

import time, argparse, csv, os
from collections import defaultdict
from math import fabs

# Simple EMA predictor
class EMA:
    def __init__(self, alpha, init=None):
        self.alpha = alpha
        self.v = init
    def update(self, x):
        if self.v is None: self.v = x
        else: self.v = self.alpha * x + (1-self.alpha)*self.v
        return self.v

def read_proc_stat():
    with open("/proc/stat") as f:
        lines = f.readlines()
    stats = {}
    for line in lines:
        if not line.startswith("cpu") or line.startswith("cpu "): continue
        parts = line.split()
        cid = int(parts[0][3:])
        vals = [int(x) for x in parts[1:11]]
        busy = vals[0]+vals[1]+vals[2]+vals[5]+vals[6]
        idle = vals[3]+vals[4]
        stats[cid] = (busy, idle)
    return stats

def util_delta(prev, now, cpu):
    pb, pi = prev[cpu]; nb, ni = now[cpu]
    busy = nb - pb; idle = ni - pi
    t = busy + idle
    return 0.0 if t<=0 else max(0.0, min(1.0, busy / t))

# Simulated freq table (fractions mapped to kHz for reporting)
SIM_FREQ_KHZ = [300000, 800000, 1200000, 1800000, 2400000]  # example steps
def pick_freq_from_frac(frac):
    idx = int(round(frac * (len(SIM_FREQ_KHZ)-1)))
    idx = max(0, min(len(SIM_FREQ_KHZ)-1, idx))
    return SIM_FREQ_KHZ[idx], idx

# A simple linear-ish power model: P = P_idle + alpha * freq_frac^2 * P_dyn_scale + beta*util
P_IDLE = 5.0    # watts baseline per active core
P_DYN_SCALE = 15.0
BETA_UTIL = 2.0

def estimate_power_per_core(freq_idx, util):
    frac = freq_idx / (len(SIM_FREQ_KHZ)-1)
    p = P_IDLE + P_DYN_SCALE * (frac**2) + BETA_UTIL * util
    return p

def main(args):
    interval = args.interval
    duration = args.duration
    ema_alpha = args.ema
    # init
    cpus = []
    i = 0
    while os.path.exists(f"/proc/stat"):
        s = open("/proc/stat").read().splitlines()
        # get cpu count from /proc/stat
        for line in s:
            if line.startswith("cpu ") :
                continue
            if line.startswith("cpu"):
                pass
        break
    # determine cpu count by reading /proc/stat
    with open("/proc/stat") as f:
        cpu_lines = [l for l in f.readlines() if l.startswith("cpu") and not l.startswith("cpu ")]
    cpus = [int(l.split()[0][3:]) for l in cpu_lines]
    if not cpus:
        print("No cpus found in /proc/stat; exiting")
        return
    max_cpu = max(cpus)
    cpu_list = list(range(max_cpu+1))
    prev = read_proc_stat()
    # initial sleep to have delta
    time.sleep(interval)
    prev = prev
    ema = {c: EMA(ema_alpha, 0.0) for c in cpu_list}
    t_end = time.time() + duration
    # Open CSV
    out = args.out
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="") as csvf:
        w = csv.writer(csvf)
        header = ["t","wall_time","cpu","util_ema","chosen_freq_khz","freq_idx","est_power_w"]
        w.writerow(header)
        while time.time() < t_end:
            now = read_proc_stat()
            wall = time.time()
            total_power = 0.0
            for c in cpu_list:
                if c not in now or c not in prev:
                    continue
                u = util_delta(prev, now, c)
                ue = ema[c].update(u)
                # simple policy: freq fraction = clamp(ue * 1.0)
                frac = ue
                chosen_khz, idx = pick_freq_from_frac(frac)
                p = estimate_power_per_core(idx, ue)
                total_power += p
                w.writerow([round(wall - (t_end-duration),3), wall, c, round(ue,4), chosen_khz, idx, round(p,4)])
            csvf.flush()
            prev = now
            time.sleep(interval)
    print("Finished. CSV:", out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", "-o", default="/tmp/dvfs_sim.csv")
    p.add_argument("--interval", "-i", type=float, default=0.5)
    p.add_argument("--duration", "-d", type=float, default=60.0)
    p.add_argument("--ema", type=float, default=0.35)
    args = p.parse_args()
    main(args)
