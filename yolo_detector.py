from ultralytics import YOLO
import cv2

FOOD_COCO_CLASSES = {
    46: "banana", 47: "apple", 48: "sandwich", 49: "orange",
    50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza",
    54: "donut", 55: "cake", 56: "bowl", 57: "cup",
    58: "fork", 59: "knife", 60: "spoon"
}

class YOLODetector:
    def __init__(self):
        print("Loading YOLOv8 model...")
        self.model = YOLO("yolov8n.pt")
        print("YOLOv8 loaded successfully")

    def detect(self, image_rgb):
        results = self.model(image_rgb, verbose=False)
        detections = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = self.model.names[cls_id]
                detections.append({
                    "label": label,
                    "confidence": conf,
                    "bbox": (x1, y1, x2, y2),
                    "cls_id": cls_id
                })
        return detections
    
    def draw_detections(self, image_rgb, detections):
        image = image_rgb.copy()
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cv2.rectangle(image, (x1, y1), (x2, y2), (255, 165, 0), 1)
        return image