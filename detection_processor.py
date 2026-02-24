import numpy as np

class DetectionProcessor:
    def __init__(self, conf_threshold=0.6, iou_threshold=0.45):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def process_detections(self, raw_detections, uav_telemetry):
        """
        1. Filters by confidence score.
        2. Applies Non-Maximum Suppression (NMS) to remove overlaps.
        3. Prepares data for GPS projection.
        """
        # --- Step 1: Confidence Filtering ---
        # Filter out anything below the threshold
        mask = raw_detections[:, 4] >= self.conf_threshold
        detections = raw_detections[mask]

        if len(detections) == 0:
            return []

        # --- Step 2: Non-Maximum Suppression (NMS) ---
        # Sort by confidence (highest first)
        detections = detections[detections[:, 4].argsort()[::-1]]
        keep = []

        while len(detections) > 0:
            best_box = detections[0]
            keep.append(best_box)
            if len(detections) == 1: break

            # Calculate overlap with other boxes
            ious = self._calculate_iou(best_box[:4], detections[1:, :4])
            # Keep boxes that don't overlap too much with the 'best' one
            detections = detections[1:][ious < self.iou_threshold]

        # --- Step 3: Prepare for GPS Projection & Telemetry ---
        final_output = []
        for det in keep:
            # Calculate pixel center (x_center, y_center)
            center_x = (det[0] + det[2]) / 2
            center_y = (det[1] + det[3]) / 2
            
            final_output.append({
                "pixel_center": (center_x, center_y),
                "confidence": round(float(det[4]), 3),
                "class_id": int(det[5]),
                "uav_state": uav_telemetry  # Bundling GPS/Alt for the next person
            })
            
        return final_output

    def _calculate_iou(self, box, boxes):
        """Math to determine how much two bounding boxes overlap."""
        x1 = np.maximum(box[0], boxes[:, 0])
        y1 = np.maximum(box[1], boxes[:, 1])
        x2 = np.minimum(box[2], boxes[:, 2])
        y2 = np.minimum(box[3], boxes[:, 3])
        
        intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
        area_box = (box[2] - box[0]) * (box[3] - box[1])
        area_boxes = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        
        return intersection / (area_box + area_boxes - intersection)

# --- DELIVERABLE: TEST CASES ---
if __name__ == "__main__":
    processor = DetectionProcessor(conf_threshold=0.5)

    # Mock Raw Data: [x1, y1, x2, y2, confidence, class_id]
    mock_raw = np.array([
        [100, 100, 200, 200, 0.90, 0], # Valid (Cow A)
        [105, 105, 205, 205, 0.85, 0], # Overlap with Cow A (Should be removed by NMS)
        [500, 500, 600, 600, 0.20, 0]  # Too weak (Should be removed by Confidence Filter)
    ])

    # Mock UAV Telemetry from flight controller
    mock_telemetry = {
        "lat": 27.527, 
        "lon": -99.491, 
        "alt": 15.0,   # 15 meters high
        "heading": 90  # Facing East
    }

    results = processor.process_detections(mock_raw, mock_telemetry)

    print(f"--- POST-PROCESSING REPORT ---")
    print(f"Initial Detections: {len(mock_raw)}")
    print(f"Final Clean Detections: {len(results)}")
    for i, res in enumerate(results):
        print(f"Detection {i+1}: Center {res['pixel_center']} | Conf: {res['confidence']}")