import time
import subprocess

start = time.time()
subprocess.run(["python", "producer/producer.py", "--input-file", "producer/creditcard.csv", "--num-records", "1000000", "--rate", "2000", "--bootstrap-server", "localhost:9092", "--topic", "transactions"])
end = time.time()
print(f"Time for 1M records: {end - start} seconds")