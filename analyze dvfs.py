import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("/tmp/dvfs_sim.csv")
interval = 0.5
energy = (df['power_w'] * interval).sum()
print(f"Estimated energy (J): {energy:.2f}")
print(df.groupby('cpu')['power_w'].mean())

plt.figure(figsize=(10,4))
plt.plot(df['t'], df['power_w'], '.', alpha=0.4)
plt.xlabel("Time (s)")
plt.ylabel("Power (W)")
plt.title("Simulated DVFS Power Trace")
plt.tight_layout()
plt.show()
