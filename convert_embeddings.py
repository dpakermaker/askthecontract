import pickle
import numpy as np
import os

PKL_PATH = os.path.join("contracts", "NAC", "embeddings.pkl")
NPY_PATH = os.path.join("contracts", "NAC", "embeddings.npy")

print(f"Loading {PKL_PATH}...")
with open(PKL_PATH, "rb") as f:
    embeddings = pickle.load(f)

print(f"  Type: {type(embeddings)}")
print(f"  Length: {len(embeddings)}")

arr = np.array(embeddings, dtype=np.float32)
print(f"  Shape: {arr.shape}")
print(f"  Numpy size: {arr.nbytes / 1024 / 1024:.1f} MB")

np.save(NPY_PATH, arr)
file_size = os.path.getsize(NPY_PATH) / 1024 / 1024
print(f"  Saved to {NPY_PATH} ({file_size:.1f} MB)")
print("Done!")