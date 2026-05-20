NUTRITION_DB = {
    "biryani": {"calories": 185, "protein": 7, "carbs": 22, "fat": 8},
    "karahi": {"calories": 210, "protein": 15, "carbs": 5, "fat": 14},
    "chicken_curry": {"calories": 190, "protein": 16, "carbs": 6, "fat": 12}, # Added for custom layer
    "daal": {"calories": 116, "protein": 8, "carbs": 18, "fat": 2},
    "nihari": {"calories": 195, "protein": 14, "carbs": 6, "fat": 13},
    "roti": {"calories": 264, "protein": 9, "carbs": 55, "fat": 3},
    "naan": {"calories": 310, "protein": 10, "carbs": 58, "fat": 6},
    "raita": {"calories": 52, "protein": 3, "carbs": 5, "fat": 2},
    "salad": {"calories": 20, "protein": 1, "carbs": 4, "fat": 0},
    "rice": {"calories": 130, "protein": 3, "carbs": 28, "fat": 0},
    "halwa": {"calories": 350, "protein": 4, "carbs": 48, "fat": 16},
    "puri": {"calories": 280, "protein": 5, "carbs": 35, "fat": 13},
    "qeema": {"calories": 230, "protein": 18, "carbs": 4, "fat": 16},
    "chai": {"calories": 45, "protein": 2, "carbs": 6, "fat": 2},
    "paratha": {"calories": 300, "protein": 7, "carbs": 42, "fat": 12},
    "samosa": {"calories": 262, "protein": 5, "carbs": 28, "fat": 14},
    "chaat": {"calories": 150, "protein": 4, "carbs": 25, "fat": 4},
    "lassi": {"calories": 100, "protein": 4, "carbs": 12, "fat": 4},
    "kebab": {"calories": 195, "protein": 16, "carbs": 8, "fat": 11},
    "korma": {"calories": 220, "protein": 14, "carbs": 6, "fat": 15},
    "kheer": {"calories": 180, "protein": 5, "carbs": 30, "fat": 5},
    "gol gappay": {"calories": 180, "protein": 3, "carbs": 28, "fat": 7},
    "pani puri": {"calories": 180, "protein": 3, "carbs": 28, "fat": 7},
    "chana": {"calories": 164, "protein": 9, "carbs": 27, "fat": 3},
    "aloo": {"calories": 77, "protein": 2, "carbs": 17, "fat": 0},
    "halwa puri": {"calories": 320, "protein": 6, "carbs": 40, "fat": 15},
    "anda": {"calories": 155, "protein": 13, "carbs": 1, "fat": 11},
    "omelette": {"calories": 180, "protein": 11, "carbs": 2, "fat": 14},       # Added for custom layer
    "fish": {"calories": 136, "protein": 20, "carbs": 0, "fat": 6},
    "seekh kebab": {"calories": 220, "protein": 18, "carbs": 5, "fat": 14},
    "shami kebab": {"calories": 200, "protein": 15, "carbs": 8, "fat": 12},
    "pulao": {"calories": 160, "protein": 4, "carbs": 30, "fat": 4},
    "mutton": {"calories": 250, "protein": 20, "carbs": 0, "fat": 18},
    "paya": {"calories": 175, "protein": 16, "carbs": 2, "fat": 12},
    "haleem": {"calories": 180, "protein": 14, "carbs": 18, "fat": 6},
    "zarda": {"calories": 280, "protein": 3, "carbs": 52, "fat": 8},
    "gulab jamun": {"calories": 175, "protein": 3, "carbs": 30, "fat": 6},
}

FOOD_ALIASES = {
    "rice": "rice",
    "chicken_curry": "chicken_curry",
    "chicken": "karahi",
    "meat": "karahi",
    "bread": "roti",
    "flatbread": "roti",
    "soup": "daal",
    "lentil": "daal",
    "yogurt": "raita",
    "salad": "salad",
    "curry": "chicken_curry", # Maps standard global "curry" predictions cleanly
    "dumpling": "samosa",
    "pastry": "samosa",
    "cake": "halwa",
    "dessert": "kheer",
    "beverage": "chai",
    "drink": "lassi",
    "sandwich": "paratha",
    "wrap": "paratha",
    "meatball": "kebab",
    "stew": "nihari",
    "donut": "gol gappay",
    "puri": "gol gappay",
    "fried dough": "gol gappay",
    "pretzel": "gol gappay",
    "bagel": "naan",
    "meatloaf": "haleem",
    "beef": "mutton",
    "lamb": "mutton",
    "pork": "mutton",
    "fish": "fish",
    "egg": "anda",
    "omelette": "omelette",
    "fried egg": "anda",
    "pilaf": "pulao",
    "pudding": "kheer",
    "cake": "zarda",
}

def get_nutrition(food_name):
    food_lower = food_name.lower().strip().replace(" ", "_")
    
    # 1. Direct key match check
    if food_lower in NUTRITION_DB:
        return NUTRITION_DB[food_lower], food_lower
        
    # Revert back to spaces for string scanning loop down below
    food_spaces = food_lower.replace("_", " ")
    
    # 2. Sequential Alias Substring checking 
    for alias, mapped in FOOD_ALIASES.items():
        alias_clean = alias.replace("_", " ")
        if alias_clean in food_spaces:
            return NUTRITION_DB[mapped], mapped
            
    # 3. Safe fallback boundary
    return NUTRITION_DB["rice"], "rice"