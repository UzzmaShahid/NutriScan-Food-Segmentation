import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
import threading
import time
import os
import datetime
from nutrition_db import get_nutrition
from sam_engine import SAMEngine
from yolo_detector import YOLODetector
from classifier import FoodClassifier
from nutrition_calc import NutritionCalculator
from pdf_exporter import PDFExporter

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "orange": "#D85A30",
    "orange_dark": "#B84820",
    "bg_dark": "#0f0f1a",
    "bg_card": "#1a1a2e",
    "bg_card2": "#16213e",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b0",
    "blue": "#378ADD",
    "green": "#639922",
    "amber": "#BA7517",
    "red": "#993C1D",
    "border": "#2a2a4a",
}

SEGMENT_COLORS = [
    (216, 90, 48),
    (55, 138, 221),
    (99, 153, 34),
    (186, 117, 23),
    (153, 60, 29),
    (147, 51, 234),
    (236, 72, 153),
]


class FoodItemCard(ctk.CTkFrame):
    def __init__(self, parent, item_data, index, color,
                 on_gram_change, on_delete, **kwargs):
        super().__init__(parent, **kwargs)
        self.item_data = item_data
        self.index = index
        self.on_gram_change = on_gram_change
        self.on_delete = on_delete
        self.color_hex = "#{:02x}{:02x}{:02x}".format(*color)
        self._build()

    def _build(self):
        self.configure(
            fg_color=COLORS["bg_card2"],
            corner_radius=10,
            border_width=1,
            border_color=self.color_hex
        )
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(top, text="●", text_color=self.color_hex,
                     font=ctk.CTkFont(size=14), width=20).pack(side="left")

        ctk.CTkLabel(top,
                     text=self.item_data["mapped_name"].title(),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=6)

        conf_pct = round(self.item_data["confidence"] * 100)
        ctk.CTkLabel(top, text=f"{conf_pct}%",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["green"],
                     fg_color="#1a2e1a", corner_radius=8,
                     width=36, height=20).pack(side="left")

        ctk.CTkButton(top, text="✕", width=24, height=24,
                      fg_color="transparent",
                      hover_color=COLORS["bg_card"],
                      text_color=COLORS["text_secondary"],
                      font=ctk.CTkFont(size=11),
                      command=lambda: self.on_delete(self.index)
                      ).pack(side="right")

        gram_row = ctk.CTkFrame(self, fg_color="transparent")
        gram_row.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(gram_row, text="Grams:",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_secondary"]).pack(side="left")

        self.gram_var = tk.StringVar(value="100")
        entry = ctk.CTkEntry(gram_row, textvariable=self.gram_var,
                             width=60, height=26,
                             font=ctk.CTkFont(size=12),
                             fg_color=COLORS["bg_card"],
                             border_color=self.color_hex)
        entry.pack(side="left", padx=8)
        entry.bind("<Return>", self._fire_change)
        entry.bind("<FocusOut>", self._fire_change)

        ctk.CTkLabel(gram_row, text="g",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_secondary"]).pack(side="left")

        self.cal_label = ctk.CTkLabel(
            gram_row,
            text=f"{self.item_data.get('calories', 0)} kcal",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.color_hex)
        self.cal_label.pack(side="right")

    def _fire_change(self, event=None):
        try:
            g = int(self.gram_var.get())
            if g > 0:
                self.on_gram_change(self.index, g)
        except ValueError:
            pass

    def update_calories(self, cal):
        self.cal_label.configure(text=f"{cal} kcal")


class NutriScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NutriScan PK")
        self.geometry("1200x760")
        self.minsize(1000, 650)
        self.configure(fg_color=COLORS["bg_dark"])

        self.original_image = None
        self.annotated_image = None
        self.image_scale_x = 1.0
        self.image_scale_y = 1.0
        self.segments = []
        self.food_cards = []
        self.is_processing = False
        self.daily_goal = 2000
        self.meal_history = []
        self.current_photo = None

        self.sam = None
        self.yolo = None
        self.classifier = None
        self.models_ready = False
        self.calc = NutritionCalculator()
        self.pdf_exp = PDFExporter()

        self._build_ui()
        self._load_models_async()

    # ── UI BUILD ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_left(body)
        self._build_center(body)
        self._build_right(body)

    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=COLORS["bg_card"],
                           height=56, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16)

        logo = ctk.CTkFrame(inner, fg_color="transparent")
        logo.pack(side="left", pady=8)

        ctk.CTkLabel(logo, text="🍽",
                     font=ctk.CTkFont(size=22),
                     fg_color=COLORS["orange"],
                     corner_radius=8, width=36, height=36).pack(side="left")

        ctk.CTkLabel(logo, text="  NutriScan ",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        ctk.CTkLabel(logo, text="PK",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=COLORS["orange"]).pack(side="left")

        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", pady=8)

        self.status_label = ctk.CTkLabel(
            right, text="⏳ Loading AI models...",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["amber"])
        self.status_label.pack(side="left", padx=16)

        ctk.CTkLabel(right,
                     text=datetime.datetime.now().strftime("%d %B %Y"),
                     font=ctk.CTkFont(size=12),
                     text_color=COLORS["text_secondary"]).pack(side="left", padx=8)

        ctk.CTkButton(right, text="📋 Meal History",
                      width=120, height=32,
                      fg_color="transparent",
                      border_width=1,
                      border_color=COLORS["border"],
                      hover_color=COLORS["bg_card2"],
                      font=ctk.CTkFont(size=12),
                      command=self._show_history).pack(side="left", padx=8)

    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"],
                            corner_radius=12, width=240)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_propagate(False)

        # Goal ring
        goal_f = ctk.CTkFrame(left, fg_color=COLORS["bg_card2"], corner_radius=10)
        goal_f.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(goal_f, text="DAILY GOAL",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_secondary"]).pack(pady=(8, 4))

        self.ring_canvas = tk.Canvas(goal_f, width=100, height=100,
                                     bg=COLORS["bg_card2"],
                                     highlightthickness=0)
        self.ring_canvas.pack()
        self._draw_ring(0)

        self.ring_cal_label = ctk.CTkLabel(
            goal_f, text=f"0 / {self.daily_goal} kcal",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_primary"])
        self.ring_cal_label.pack(pady=(4, 4))

        stats = ctk.CTkFrame(goal_f, fg_color="transparent")
        stats.pack(fill="x", padx=8, pady=(0, 8))
        stats.grid_columnconfigure((0, 1), weight=1)

        self.stat_protein = self._mini_stat(stats, "Protein", "0g", COLORS["blue"], 0, 0)
        self.stat_carbs = self._mini_stat(stats, "Carbs", "0g", COLORS["amber"], 0, 1)
        self.stat_fat = self._mini_stat(stats, "Fat", "0g", COLORS["red"], 1, 0)
        self.stat_remain = self._mini_stat(stats, "Left", str(self.daily_goal), COLORS["green"], 1, 1)

        # Goal input
        gr = ctk.CTkFrame(left, fg_color="transparent")
        gr.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(gr, text="Goal:",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self.goal_var = tk.StringVar(value="2000")
        ge = ctk.CTkEntry(gr, textvariable=self.goal_var,
                          width=70, height=26, font=ctk.CTkFont(size=12),
                          fg_color=COLORS["bg_card2"])
        ge.pack(side="left", padx=6)
        ge.bind("<Return>", self._update_goal)
        ctk.CTkLabel(gr, text="kcal", font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_secondary"]).pack(side="left")

        # Buttons
        ctk.CTkButton(left, text="📂  Upload Image",
                      height=40, fg_color=COLORS["orange"],
                      hover_color=COLORS["orange_dark"],
                      font=ctk.CTkFont(size=13, weight="bold"),
                      corner_radius=8,
                      command=self._upload_image
                      ).pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkButton(left, text="🔄  Clear & Reset",
                      height=34, fg_color="transparent",
                      border_width=1, border_color=COLORS["border"],
                      hover_color=COLORS["bg_card2"],
                      font=ctk.CTkFont(size=12), corner_radius=8,
                      command=self._clear_all
                      ).pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(left, text="DETECTED ITEMS",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=COLORS["text_secondary"]
                     ).pack(anchor="w", padx=12, pady=(0, 6))

        self.food_scroll = ctk.CTkScrollableFrame(
            left, fg_color="transparent",
            scrollbar_button_color=COLORS["border"])
        self.food_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.click_hint = ctk.CTkLabel(
            self.food_scroll,
            text="📍 Click on food items\nin the image to detect",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="center")
        self.click_hint.pack(pady=20)


    def _mini_stat(self, parent, label, value, color, row, col):
        f = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=6)
        f.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
        lbl = ctk.CTkLabel(f, text=value,
                           font=ctk.CTkFont(size=13, weight="bold"),
                           text_color=color)
        lbl.pack(pady=(6, 0))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=10),
                     text_color=COLORS["text_secondary"]).pack(pady=(0, 6))
        return lbl

    def _build_center(self, parent):
        center = ctk.CTkFrame(parent, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", padx=4)
        center.grid_rowconfigure(1, weight=1)
        center.grid_columnconfigure(0, weight=1)

        # Info bar
        info = ctk.CTkFrame(center, fg_color=COLORS["bg_card"],
                            corner_radius=8, height=36)
        info.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        info.grid_propagate(False)

        ii = ctk.CTkFrame(info, fg_color="transparent")
        ii.pack(fill="both", expand=True, padx=12)

        self.seg_count_label = ctk.CTkLabel(
            ii, text="⬡ 0 segments",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"])
        self.seg_count_label.pack(side="left")

        ctk.CTkLabel(ii, text="|", text_color=COLORS["border"],
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=8)

        ctk.CTkLabel(ii,
                     text="SAM vit_b  •  YOLOv8n  •  ViT Classifier",
                     font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_secondary"]).pack(side="left")

        self.processing_label = ctk.CTkLabel(
            ii, text="", font=ctk.CTkFont(size=11),
            text_color=COLORS["amber"])
        self.processing_label.pack(side="right")

        # Canvas
        self.canvas_frame = ctk.CTkFrame(
            center, fg_color=COLORS["bg_card"], corner_radius=12)
        self.canvas_frame.grid(row=1, column=0, sticky="nsew")

        self.image_label = ctk.CTkLabel(
            self.canvas_frame,
            text="📂  Upload a food image to begin\n\nClick 'Upload Image' on the left",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
            fg_color="transparent")
        self.image_label.pack(fill="both", expand=True, padx=40, pady=30)
        self.image_label.bind("<Button-1>", self._on_canvas_click)

    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"],
                            corner_radius=12, width=220)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        right.grid_propagate(False)

        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(4, 12), side="bottom")

        tc = ctk.CTkFrame(right, fg_color=COLORS["orange"], corner_radius=10)
        tc.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(tc, text="TOTAL CALORIES",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color="#FAECE7").pack(pady=(10, 0))

        self.total_cal_label = ctk.CTkLabel(
            tc, text="0",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="white")
        self.total_cal_label.pack()

        ctk.CTkLabel(tc, text="kcal this meal",
                    font=ctk.CTkFont(size=11),
                    text_color="#FAECE7").pack(pady=(0, 10))

        ctk.CTkLabel(right, text="MACRONUTRIENTS",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=COLORS["text_secondary"]
                    ).pack(anchor="w", padx=12, pady=(4, 6))

        self.macro_protein = self._macro_bar(right, "Protein", COLORS["blue"], 50)
        self.macro_carbs = self._macro_bar(right, "Carbs", COLORS["amber"], 250)
        self.macro_fat = self._macro_bar(right, "Fat", COLORS["red"], 65)

        ctk.CTkLabel(right, text="TODAY'S MEALS",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=COLORS["text_secondary"]
                    ).pack(anchor="w", padx=12, pady=(8, 4))

        self.history_frame = ctk.CTkScrollableFrame(
            right, fg_color="transparent", height=80,
            scrollbar_button_color=COLORS["border"])
        self.history_frame.pack(fill="x", padx=8, pady=(0, 4))

        ctk.CTkLabel(self.history_frame, text="No meals logged yet",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS["text_secondary"]).pack(pady=8)



        ctk.CTkButton(btn_frame, text="🗑  Clear History",
                    height=28, fg_color="transparent",
                    border_width=1, border_color=COLORS["border"],
                    hover_color=COLORS["bg_card2"],
                    font=ctk.CTkFont(size=11), corner_radius=8,
                    command=self._clear_history
                    ).pack(fill="x", pady=(0, 4))

        ctk.CTkButton(btn_frame, text="✅  Log This Meal",
                    height=34, fg_color=COLORS["green"],
                    hover_color="#2d6b10",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    corner_radius=8,
                    command=self._log_meal
                    ).pack(fill="x", pady=(0, 4))

        self.export_btn = ctk.CTkButton(
            btn_frame, text="📄  Export PDF Report",
            height=40, fg_color=COLORS["orange"],
            hover_color=COLORS["orange_dark"],
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8, command=self._export_pdf,
            state="normal")
        self.export_btn.pack(fill="x")


    def _macro_bar(self, parent, label, color, max_val):
        f = ctk.CTkFrame(parent, fg_color=COLORS["bg_card2"], corner_radius=8)
        f.pack(fill="x", padx=12, pady=3)

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(row, text=label,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=color).pack(side="left")

        val = ctk.CTkLabel(row, text="0g",
                           font=ctk.CTkFont(size=16, weight="bold"),
                           text_color=color)
        val.pack(side="right")

        bg = ctk.CTkFrame(f, fg_color=COLORS["bg_card"], height=4, corner_radius=2)
        bg.pack(fill="x", padx=10, pady=(0, 8))

        fill = tk.Frame(bg, bg=color, height=4)
        fill.place(x=0, y=0, relheight=1, width=0)

        return {"label": val, "bar": fill, "bg": bg, "max": max_val}

    # ── DRAWING ───────────────────────────────────────────────────────────────

    def _draw_ring(self, pct):
        self.ring_canvas.delete("all")
        cx, cy, r = 50, 50, 36
        self.ring_canvas.create_arc(
            cx-r, cy-r, cx+r, cy+r,
            start=0, extent=359.9,
            outline=COLORS["border"], width=8, style="arc")
        if pct > 0:
            color = COLORS["orange"] if pct <= 100 else COLORS["red"]
            self.ring_canvas.create_arc(
                cx-r, cy-r, cx+r, cy+r,
                start=90, extent=-min(359.9, pct/100*359.9),
                outline=color, width=8, style="arc")
        self.ring_canvas.create_text(cx, cy-8, text=f"{pct}%",
                                     fill=COLORS["text_primary"],
                                     font=("Helvetica", 13, "bold"))
        self.ring_canvas.create_text(cx, cy+10, text="of goal",
                                     fill=COLORS["text_secondary"],
                                     font=("Helvetica", 9))

    def _animate_ring(self, target, current=0):
        if current < target:
            self._draw_ring(current)
            self.after(10, lambda: self._animate_ring(target, current+2))
        else:
            self._draw_ring(target)

    def _animate_number(self, label, target, current=0):
        step = max(1, target // 20)
        if current < target:
            label.configure(text=str(current))
            self.after(25, lambda: self._animate_number(label, target, min(current+step, target)))
        else:
            label.configure(text=str(target))

    def _update_macro_bar(self, md, value):
        md["label"].configure(text=f"{value}g")
        pct = min(1.0, value / md["max"])
        bw = md["bg"].winfo_width()
        if bw > 10:
            md["bar"].place(x=0, y=0, relheight=1, width=int(bw*pct))

    # ── MODEL LOADING ─────────────────────────────────────────────────────────

    def _load_models_async(self):
        def load():
            try:
                self._set_status("⏳ Loading YOLOv8...", COLORS["amber"])
                self.yolo = YOLODetector()
                self._set_status("⏳ Loading SAM...", COLORS["amber"])
                self.sam = SAMEngine()
                self._set_status("⏳ Loading Classifier...", COLORS["amber"])
                self.classifier = FoodClassifier()
                self.models_ready = True
                self._set_status("✅ All models ready — upload an image!", COLORS["green"])
            except Exception as e:
                self._set_status(f"❌ Error: {str(e)[:50]}", COLORS["red"])
        threading.Thread(target=load, daemon=True).start()

    def _set_status(self, text, color):
        self.after(0, lambda: self.status_label.configure(
            text=text, text_color=color))

    # ── IMAGE UPLOAD ──────────────────────────────────────────────────────────

    def _upload_image(self):
        if not self.models_ready:
            messagebox.showwarning("Please Wait", "Models still loading, please wait.")
            return
        path = filedialog.askopenfilename(
            title="Select Food Image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp"),
                       ("All files", "*.*")])
        if not path:
            return
        self._clear_all()
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Error", "Could not load image.")
            return
        self.original_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.annotated_image = self.original_image.copy()
        self.processing_label.configure(text="🔄 Preparing...")

        def prepare():
            self.sam.set_image(self.original_image)
            dets = self.yolo.detect(self.original_image)
            if dets:
                self.annotated_image = self.yolo.draw_detections(
                    self.original_image.copy(), dets)
            self.after(0, self._show_image)
            self.after(0, lambda: self.processing_label.configure(text=""))
            self.after(0, lambda: self._set_status(
                f"✅ Ready — YOLO found {len(dets)} objects. Click to segment.",
                COLORS["green"]))
        threading.Thread(target=prepare, daemon=True).start()

    def _show_image(self):
        if self.annotated_image is None:
            return
        self.canvas_frame.update()
        cw = max(100, self.canvas_frame.winfo_width() - 80)
        ch = max(100, self.canvas_frame.winfo_height() - 60)
        h, w = self.annotated_image.shape[:2]
        scale = min(cw/w, ch/h)
        nw, nh = int(w*scale), int(h*scale)
        self.image_scale_x = w / nw
        self.image_scale_y = h / nh
        resized = cv2.resize(
            self.annotated_image, (nw, nh),
            interpolation=cv2.INTER_LANCZOS4)
        pil = Image.fromarray(resized)
        self.current_photo = ctk.CTkImage(pil, size=(nw, nh))
        self.image_label.configure(text="")
        self.image_label.configure(image=self.current_photo)

    # ── CLICK & SEGMENT ───────────────────────────────────────────────────────

    def _on_canvas_click(self, event):
        if self.original_image is None or self.is_processing:
            return
        if not self.models_ready:
            return
        x = int(event.x * self.image_scale_x)
        y = int(event.y * self.image_scale_y)
        h, w = self.original_image.shape[:2]
        x = max(0, min(x, w-1))
        y = max(0, min(y, h-1))
        self._process_click(x, y)

    def _process_click(self, x, y):
        self.is_processing = True
        self.processing_label.configure(text="🔄 Segmenting...")

        def process():
            t0 = time.time()
            result = self.sam.segment_point(x, y)
            if result is None:
                self.after(0, lambda: setattr(self, 'is_processing', False))
                return
            mask, score = result
            color = SEGMENT_COLORS[len(self.segments) % len(SEGMENT_COLORS)]
            self.annotated_image = self.sam.create_colored_overlay(
                self.annotated_image, mask, color)
            crop = self.sam.get_mask_crop(self.original_image, mask)
            bbox = self.sam.get_mask_bbox(mask)
            clf = self.classifier.classify(crop)
            nutrition, _ = get_nutrition(clf["mapped_name"])
            item = self.calc.add_item(clf["mapped_name"], nutrition, 100)
            elapsed = round(time.time() - t0, 1)
            if bbox:
                x1, y1, x2, y2 = bbox
                label_text = clf["mapped_name"].title()
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.55
                thickness = 1
                (tw, th), baseline = cv2.getTextSize(
                    label_text, font, font_scale, thickness)
                lx = max(x1, 5)
                ly = max(y1 - 10, th + 10)
                pad = 5
                cv2.rectangle(
                    self.annotated_image,
                    (lx - pad, ly - th - pad),
                    (lx + tw + pad, ly + pad),
                    color, -1)
                cv2.rectangle(
                    self.annotated_image,
                    (lx - pad, ly - th - pad),
                    (lx + tw + pad, ly + pad),
                    (255, 255, 255), 1)
                cv2.putText(
                    self.annotated_image, label_text,
                    (lx, ly),
                    font, font_scale,
                    (255, 255, 255), thickness,
                    cv2.LINE_AA)
            seg = {"mask": mask, "color": color, "bbox": bbox,
                   "classification": clf, "nutrition_per_100g": nutrition}
            self.segments.append(seg)
            idx = len(self.segments) - 1
            self.after(0, self._show_image)
            self.after(0, lambda: self._add_food_card(clf, color, idx, nutrition))
            self.after(0, self._update_nutrition_display)
            self.after(0, lambda: self.processing_label.configure(
                text=f"✓ Done in {elapsed}s"))
            self.after(0, lambda: self.seg_count_label.configure(
                text=f"⬡ {len(self.segments)} segments"))
            self.after(0, lambda: setattr(self, 'is_processing', False))
        threading.Thread(target=process, daemon=True).start()

    # ── FOOD CARDS ────────────────────────────────────────────────────────────

    def _add_food_card(self, clf, color, index, nutrition):
        try:
            if self.click_hint.winfo_exists():
                self.click_hint.destroy()
        except Exception:
            pass

        item_data = {**clf, "grams": 100,
                     "calories": nutrition["calories"],
                     "nutrition_per_100g": nutrition}
        card = FoodItemCard(
            self.food_scroll, item_data, index, color,
            on_gram_change=self._on_gram_change,
            on_delete=self._on_delete_item,
            fg_color=COLORS["bg_card2"], corner_radius=10)
        card.pack(fill="x", pady=4)
        self.food_cards.append(card)
        self.export_btn.configure(state="normal")

    def _on_gram_change(self, index, grams):
        if 0 <= index < len(self.segments):
            nut = self.segments[index]["nutrition_per_100g"]
            self.calc.update_item_grams(index, grams, nut)
            self._update_nutrition_display()
            if index < len(self.food_cards):
                cal = round(nut["calories"] * grams / 100)
                self.food_cards[index].update_calories(cal)

    def _on_delete_item(self, index):
        if 0 <= index < len(self.calc.items):
            self.calc.items.pop(index)
            self._update_nutrition_display()
        if 0 <= index < len(self.food_cards):
            self.food_cards[index].destroy()
            self.food_cards.pop(index)

    # ── NUTRITION DISPLAY ─────────────────────────────────────────────────────

    def _update_nutrition_display(self):
        totals = self.calc.get_totals()
        pct = self.calc.get_goal_percentage()
        self._animate_number(self.total_cal_label, totals["calories"])
        self._animate_ring(pct)
        self.ring_cal_label.configure(
            text=f"{totals['calories']} / {self.daily_goal} kcal")
        self.stat_protein.configure(text=f"{totals['protein']}g")
        self.stat_carbs.configure(text=f"{totals['carbs']}g")
        self.stat_fat.configure(text=f"{totals['fat']}g")
        self.stat_remain.configure(
            text=str(max(0, self.daily_goal - totals["calories"])))
        self.after(120, lambda: self._update_macro_bar(
            self.macro_protein, totals["protein"]))
        self.after(120, lambda: self._update_macro_bar(
            self.macro_carbs, totals["carbs"]))
        self.after(120, lambda: self._update_macro_bar(
            self.macro_fat, totals["fat"]))

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _update_goal(self, event=None):
        try:
            g = int(self.goal_var.get())
            if g > 0:
                self.daily_goal = g
                self.calc.daily_goal = g
                self._update_nutrition_display()
        except ValueError:
            pass

    def _log_meal(self):
        if not self.calc.items:
            return
        totals = self.calc.get_totals()
        now = datetime.datetime.now().strftime("%I:%M %p")
        self.meal_history.append({
            "time": now,
            "items": list(self.calc.items),
            "totals": totals
        })
        self._refresh_history()
        messagebox.showinfo("Logged",
                            f"Meal logged at {now}\n{totals['calories']} kcal recorded.")

    def _refresh_history(self):
        for w in self.history_frame.winfo_children():
            w.destroy()
        if not self.meal_history:
            ctk.CTkLabel(self.history_frame, text="No meals logged yet",
                         font=ctk.CTkFont(size=11),
                         text_color=COLORS["text_secondary"]).pack(pady=8)
            return
        for meal in self.meal_history:
            row = ctk.CTkFrame(self.history_frame,
                               fg_color=COLORS["bg_card2"], corner_radius=6)
            row.pack(fill="x", pady=2)
            ir = ctk.CTkFrame(row, fg_color="transparent")
            ir.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(ir, text=meal["time"],
                         font=ctk.CTkFont(size=11),
                         text_color=COLORS["text_secondary"]).pack(side="left")
            ctk.CTkLabel(ir, text=f"{meal['totals']['calories']} kcal",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=COLORS["orange"]).pack(side="right")

    def _show_history(self):
        win = ctk.CTkToplevel(self)
        win.title("Meal History")
        win.geometry("420x500")
        win.configure(fg_color=COLORS["bg_dark"])
        win.grab_set()
        win.focus()
        win.lift()
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="Today's Meal History",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=COLORS["text_primary"]).pack(pady=16)

        if not self.meal_history:
            ctk.CTkLabel(win, text="No meals logged yet.\nLog a meal first using the button on the left.",
                        font=ctk.CTkFont(size=13),
                        text_color=COLORS["text_secondary"],
                        justify="center").pack(pady=40)
            ctk.CTkButton(win, text="Close", command=win.destroy,
                        fg_color=COLORS["orange"],
                        hover_color=COLORS["orange_dark"]).pack(pady=10)
            return

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=8)

        total_day = 0
        for i, meal in enumerate(self.meal_history):
            card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"],
                                corner_radius=10)
            card.pack(fill="x", pady=6)

            hdr = ctk.CTkFrame(card, fg_color=COLORS["bg_card2"],
                            corner_radius=8)
            hdr.pack(fill="x", padx=8, pady=(8, 4))

            hi = ctk.CTkFrame(hdr, fg_color="transparent")
            hi.pack(fill="x", padx=10, pady=6)

            ctk.CTkLabel(hi, text=f"Meal {i+1} — {meal['time']}",
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=COLORS["text_primary"]).pack(side="left")

            ctk.CTkLabel(hi, text=f"{meal['totals']['calories']} kcal",
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=COLORS["orange"]).pack(side="right")

            for it in meal["items"]:
                r = ctk.CTkFrame(card, fg_color="transparent")
                r.pack(fill="x", padx=12, pady=2)
                ctk.CTkLabel(r,
                            text=f"• {it['name'].title()} ({it['grams']}g)",
                            font=ctk.CTkFont(size=11),
                            text_color=COLORS["text_secondary"]).pack(side="left")
                ctk.CTkLabel(r, text=f"{it['calories']} kcal",
                            font=ctk.CTkFont(size=11),
                            text_color=COLORS["text_primary"]).pack(side="right")

            total_day += meal["totals"]["calories"]

        ctk.CTkLabel(win,
                    text=f"Total today: {total_day} kcal",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=COLORS["orange"]).pack(pady=8)

        ctk.CTkButton(win, text="Close", command=win.destroy,
                    fg_color=COLORS["orange"],
                    hover_color=COLORS["orange_dark"],
                    width=120).pack(pady=(0, 12))

    def _export_pdf(self):
        if not self.calc.items:
            messagebox.showwarning(
                "Nothing to Export",
                "Please upload an image and click on food items to detect them first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"NutriScan_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        if not path:
            return
        try:
            totals = self.calc.get_totals()
            self.pdf_exp.export(
                path, self.calc.items, totals,
                self.daily_goal, self.annotated_image)
            messagebox.showinfo("Exported", f"Report saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _clear_all(self):
        self.original_image = None
        self.annotated_image = None
        self.segments = []
        self.food_cards = []
        self.calc.clear()
        self.current_photo = None
        self.image_label.configure(image="")
        self.image_label.configure(
            text="📂  Upload a food image to begin\n\nClick 'Upload Image' on the left")
        for w in self.food_scroll.winfo_children():
            w.destroy()
        self.click_hint = ctk.CTkLabel(
            self.food_scroll,
            text="📍 Click on food items\nin the image to detect",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="center")
        self.click_hint.pack(pady=20)
        self.total_cal_label.configure(text="0")
        self.ring_cal_label.configure(text=f"0 / {self.daily_goal} kcal")
        self._draw_ring(0)
        self.stat_protein.configure(text="0g")
        self.stat_carbs.configure(text="0g")
        self.stat_fat.configure(text="0g")
        self.stat_remain.configure(text=str(self.daily_goal))
        self.seg_count_label.configure(text="⬡ 0 segments")
        self.processing_label.configure(text="")
        self.export_btn.configure(state="disabled")
        for m in [self.macro_protein, self.macro_carbs, self.macro_fat]:
            m["label"].configure(text="0g")
            m["bar"].place_forget()

    def _clear_history(self):
        self.meal_history = []
        self._refresh_history()


if __name__ == "__main__":
    app = NutriScanApp()
    app.mainloop()