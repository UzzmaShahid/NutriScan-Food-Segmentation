import torch
import cv2
import numpy as np
import customtkinter
from segment_anything import sam_model_registry, SamPredictor
from transformers import pipeline

print("PyTorch:", torch.__version__)
print("OpenCV:", cv2.__version__)
print("CustomTkinter:", customtkinter.__version__)
print("SAM: ready")
print("Hugging Face: ready")
print("\nAll systems go. Let's build.")