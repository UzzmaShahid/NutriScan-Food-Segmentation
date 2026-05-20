from transformers import pipeline
from PIL import Image
import numpy as np
from nutrition_db import get_nutrition

class FoodClassifier:
    def __init__(self):
        print("Loading global food classifier (nateraw/food)...")
        self.global_classifier = pipeline(
            "image-classification",
            model="nateraw/food",
            top_k=5
        )
        
        print("Loading custom fine-tuned classifier (samosa/curry/omelette)...")
        # Loads your new custom model weights locally from your VS Code workspace
        self.local_classifier = pipeline(
            "image-classification",
            model="./fine_tuned_food_model"
        )
        print("All Classifiers loaded successfully!")

    def classify(self, image_rgb_crop):
        pil_image = Image.fromarray(image_rgb_crop)
        pil_image = pil_image.resize((224, 224))
        
        # ---------------------------------------------------------
        # STAGE 1: Check your Custom Fine-Tuned Layer First
        # ---------------------------------------------------------
        try:
            local_results = self.local_classifier(pil_image)
            top_local_label = local_results[0]["label"].lower()
            top_local_conf = local_results[0]["score"]
            
            # Target labels from your Kaggle curated subset
            target_dishes = ["samosa", "chicken_curry", "omelette"]
            
            # Strict validation threshold to avoid false positives on non-target foods
            if top_local_label in target_dishes and top_local_conf >= 0.90:
                print(f"🎯 Custom Layer Match: {top_local_label} ({top_local_conf:.2f})")
                nutrition, mapped_name = get_nutrition(top_local_label)
                return {
                    "raw_label": top_local_label,
                    "mapped_name": mapped_name,
                    "confidence": top_local_conf,
                    "method": "custom_fine_tuned_layer",
                    "nutrition_per_100g": nutrition,
                    "all_predictions": local_results
                }
        except Exception as e:
            print(f"⚠️ Warning: Custom layer inference failed ({e}). Dropping back to global.")

        # ---------------------------------------------------------
        # STAGE 2: Original Fallback to Global nateraw/food Model
        # ---------------------------------------------------------
        results = self.global_classifier(pil_image)
        top_label = results[0]["label"].lower()
        top_conf = results[0]["score"]

        # If confidence is too low use color-based fallback
        if top_conf < 0.30:
            fallback = self._color_based_guess(image_rgb_crop)
            nutrition, mapped_name = get_nutrition(fallback)
            return {
                "raw_label": fallback,
                "mapped_name": mapped_name,
                "confidence": top_conf,
                "method": "color_analysis",
                "nutrition_per_100g": nutrition,
                "all_predictions": results
            }

        nutrition, mapped_name = get_nutrition(top_label)
        return {
            "raw_label": top_label,
            "mapped_name": mapped_name,
            "confidence": top_conf,
            "method": "classifier",
            "nutrition_per_100g": nutrition,
            "all_predictions": results
        }

    def _color_based_guess(self, image_rgb):
        avg = np.mean(image_rgb, axis=(0, 1))
        r, g, b = avg[0], avg[1], avg[2]

        # White or very light = raita or rice
        if r > 200 and g > 200 and b > 200:
            return "raita"

        # Brown or dark brown = roti or naan
        if r > 150 and g > 100 and b < 100:
            return "roti"

        # Orange red = karahi or curry
        if r > 180 and g < 130 and b < 100:
            return "karahi"

        # Deep red = nihari or qeema
        if r > 140 and g < 80 and b < 80:
            return "nihari"

        # Yellow orange = biryani or daal
        if r > 180 and g > 140 and b < 100:
            return "biryani"

        # Green = salad
        if g > r and g > b and g > 120:
            return "salad"

        # Default fallback
        return "karahi"