import torch

print(torch.backends.mps.is_available())  # MPS présent sur ce Mac ?
print(torch.backends.mps.is_built())      # PyTorch compilé avec support MPS ?

if torch.backends.mps.is_available():
    print("✅ GPU Apple Silicon utilisable")
    device = torch.device("mps")
else:
    print("❌ MPS non disponible, utilisation du CPU")
    device = torch.device("cpu")
