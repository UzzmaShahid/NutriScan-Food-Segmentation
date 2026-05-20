class NutritionCalculator:
    def __init__(self):
        self.items = []
        self.daily_goal = 2000

    def add_item(self, name, nutrition_per_100g, grams):
        factor = grams / 100
        calculated = {
            "name": name,
            "grams": grams,
            "calories": round(nutrition_per_100g["calories"] * factor),
            "protein": round(nutrition_per_100g["protein"] * factor, 1),
            "carbs": round(nutrition_per_100g["carbs"] * factor, 1),
            "fat": round(nutrition_per_100g["fat"] * factor, 1)
        }
        self.items.append(calculated)
        return calculated

    def update_item_grams(self, index, new_grams, nutrition_per_100g):
        if 0 <= index < len(self.items):
            factor = new_grams / 100
            self.items[index]["grams"] = new_grams
            self.items[index]["calories"] = round(nutrition_per_100g["calories"] * factor)
            self.items[index]["protein"] = round(nutrition_per_100g["protein"] * factor, 1)
            self.items[index]["carbs"] = round(nutrition_per_100g["carbs"] * factor, 1)
            self.items[index]["fat"] = round(nutrition_per_100g["fat"] * factor, 1)

    def get_totals(self):
        return {
            "calories": sum(i["calories"] for i in self.items),
            "protein": round(sum(i["protein"] for i in self.items), 1),
            "carbs": round(sum(i["carbs"] for i in self.items), 1),
            "fat": round(sum(i["fat"] for i in self.items), 1)
        }

    def get_goal_percentage(self):
        totals = self.get_totals()
        return min(100, round((totals["calories"] / self.daily_goal) * 100))

    def clear(self):
        self.items = []