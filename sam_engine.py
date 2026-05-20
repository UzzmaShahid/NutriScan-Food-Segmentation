import numpy as np
import cv2
from segment_anything import sam_model_registry, SamPredictor

class SAMEngine:
    def __init__(self, checkpoint_path="sam_vit_b.pth"):
        self.device = "cpu"
        print("Loading SAM model...")
        sam = sam_model_registry["vit_b"](checkpoint=checkpoint_path)
        sam.to(device=self.device)
        self.predictor = SamPredictor(sam)
        self.image_set = False
        print("SAM loaded successfully")

    def set_image(self, image_rgb):
        self.predictor.set_image(image_rgb)
        self.image_set = True

    def segment_point(self, x, y):
        if not self.image_set:
            return None
        input_point = np.array([[x, y]])
        input_label = np.array([1])
        masks, scores, _ = self.predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True
        )
        best_mask_idx = np.argmax(scores)
        return masks[best_mask_idx], scores[best_mask_idx]

    def get_mask_crop(self, image_rgb, mask):
        masked = image_rgb.copy()
        masked[~mask] = 0
        coords = np.where(mask)
        if len(coords[0]) == 0:
            return None
        y_min, y_max = coords[0].min(), coords[0].max()
        x_min, x_max = coords[1].min(), coords[1].max()
        cropped = masked[y_min:y_max+1, x_min:x_max+1]
        return cropped

    def get_mask_bbox(self, mask):
        coords = np.where(mask)
        if len(coords[0]) == 0:
            return None
        y_min, y_max = coords[0].min(), coords[0].max()
        x_min, x_max = coords[1].min(), coords[1].max()
        return x_min, y_min, x_max, y_max

    def create_colored_overlay(self, image_rgb, mask, color, alpha=0.25):
        overlay = image_rgb.copy()
        colored = np.zeros_like(image_rgb)
        colored[mask] = color
        overlay = cv2.addWeighted(overlay, 1, colored, alpha, 0)
        contours, _ = cv2.findContours(
            mask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_NONE
        )
        # Draw smooth thick outline
        cv2.drawContours(overlay, contours, -1, (255,255,255), 3)
        cv2.drawContours(overlay, contours, -1, color, 2)
        return overlay