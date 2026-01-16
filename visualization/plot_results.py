import pandas as pd
import matplotlib.pyplot as plt

# load simulated output
data = pd.read_csv("sample_output.csv")

# create plot
plt.figure()
plt.plot(data["time"], data["transactions"])
plt.xlabel("Time")
plt.ylabel("Number of Transactions")
plt.title("Simulated Streaming Output")

plt.show()
