import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------
# Energy model parameters
# -----------------------------
V_BASE = 1.0  # base voltage (V)
F_BASE = 1.0  # base frequency (normalized)
POWER_COEFF = 50  # scaling constant for energy (arbitrary units)

def estimate_power(freq_scale):
    """Estimate power (W) using simplified DVFS model: P ∝ V^2 * f"""
    voltage = V_BASE * freq_scale
    return POWER_COEFF * (voltage ** 2) * freq_scale

# -----------------------------
# Task definition
# -----------------------------
class Task:
    def __init__(self, name, arrival, burst):
        self.name = name
        self.arrival = arrival
        self.burst = burst
        self.remaining = burst
        self.start = None
        self.finish = None

# -----------------------------
# Scheduling algorithms
# -----------------------------
def fcfs(tasks):
    time, schedule = 0, []
    for t in sorted(tasks, key=lambda x: x.arrival):
        if time < t.arrival:
            time = t.arrival
        t.start = time
        time += t.burst
        t.finish = time
        schedule.append((t.name, t.start, t.finish))
    return schedule

def sjf(tasks):
    time, schedule = 0, []
    tasks_left = tasks[:]
    while tasks_left:
        ready = [t for t in tasks_left if t.arrival <= time]
        if not ready:
            time += 1
            continue
        t = min(ready, key=lambda x: x.burst)
        t.start = time
        time += t.burst
        t.finish = time
        schedule.append((t.name, t.start, t.finish))
        tasks_left.remove(t)
    return schedule

def round_robin(tasks, quantum=2):
    time, schedule = 0, []
    ready_queue = []
    tasks_left = sorted(tasks, key=lambda x: x.arrival)
    while tasks_left or ready_queue:
        while tasks_left and tasks_left[0].arrival <= time:
            ready_queue.append(tasks_left.pop(0))
        if ready_queue:
            t = ready_queue.pop(0)
            if t.start is None:
                t.start = time
            exec_time = min(quantum, t.remaining)
            time += exec_time
            t.remaining -= exec_time
            if t.remaining == 0:
                t.finish = time
            else:
                ready_queue.append(t)
            schedule.append((t.name, time - exec_time, time))
        else:
            time += 1
    return schedule

# -----------------------------
# Energy estimation
# -----------------------------
def simulate(schedule, freq_scale):
    power = estimate_power(freq_scale)
    total_energy = 0
    energy_timeline = []

    for name, start, end in schedule:
        duration = end - start
        energy = power * duration
        total_energy += energy
        for t in range(start, end):
            energy_timeline.append((t, power))

    return total_energy, energy_timeline

# -----------------------------
# Main simulation
# -----------------------------
if __name__ == "__main__":
    tasks = [
        Task("T1", 0, 5),
        Task("T2", 1, 3),
        Task("T3", 2, 8),
        Task("T4", 3, 6)
    ]

    schedulers = {
        "FCFS": fcfs,
        "SJF": sjf,
        "RoundRobin": lambda t: round_robin(t, quantum=2)
    }

    results = []
    for name, algo in schedulers.items():
        schedule = algo([Task(t.name, t.arrival, t.burst) for t in tasks])
        energy, timeline = simulate(schedule, freq_scale=0.8)
        results.append((name, energy, timeline))

    # -----------------------------
    # Plot results
    # -----------------------------
    plt.figure(figsize=(8, 5))
    for name, energy, timeline in results:
        times, powers = zip(*timeline)
        plt.plot(times, powers, label=f"{name} (E={energy:.1f})")

    plt.xlabel("Time")
    plt.ylabel("Power (arbitrary units)")
    plt.title("Energy-efficient CPU Scheduling Simulation")
    plt.legend()
    plt.grid(True)
    plt.savefig("scheduler_energy_comparison.png")
    print("✅ Saved plot: scheduler_energy_comparison.png")
    for name, energy, _ in results:
        print(f"{name}: Estimated Total Energy = {energy:.2f}")
