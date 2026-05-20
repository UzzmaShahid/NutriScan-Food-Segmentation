# NutriScan 

NutriScan is a smart food diary built to take the guesswork out of tracking calories and macros for Pakistani meals. 

Most fitness apps work great if you are logging something simple like a sandwich or an apple, but they completely fall apart when you show them a mixed plate of local food like Biryani, Omelettes, or Chicken Curry. Instead of forcing you to guess and type everything out manually, NutriScan lets you just upload a photo of your plate, tap on a dish, and let AI do the heavy lifting.

##  What It Does
* **Tap to Select:** Upload a picture of your meal and click directly on any food item.
* **Instant Smart Cut-Out:** The AI automatically cuts out the exact shape of that food, separating it from the rest of the plate.
* **Local Food Recognition:** A custom-trained model identifies regional favorites like Samosas, Omelettes, and Curries with high accuracy.
* **Macro Tracking:** Automatically calculates your daily calories, protein, carbs, and fats, updating your progress rings instantly.

##  Project Structure
```text
NUTRISCAN/
├── fine_tuned_food_model/
│   ├── config.json
│   ├── model.safetensors
│   └── preprocessor_config.json
├── dataset/
├── test_images/
├── venv/
├── .gitignore
├── app.py
├── classifier.py
├── nutrition_db.py
├── pdf_exporter.py
├── sam_engine.py
├── sam_vit_b.pth
├── test_setup.py
├── yolo_detector.py
└── yolov8n.pt
##  How to Run It Locally

### 1. Set up your environment
Create a clean virtual environment:
```bash
python -m venv venv
