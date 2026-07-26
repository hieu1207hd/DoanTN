from collections import defaultdict, deque

from ultralytics import YOLO

from utils.device import resolve_device


class HelmetDetector:
    def __init__(self, model_path, conf=0.25, device="auto"):
        self.model = YOLO(model_path)
        self.conf = conf
        self.device = resolve_device(device)
        self.names = self.model.names  # vd: {0: 'helmet', 1: 'no_helmet'}

    def detect(self, crop):
        if crop is None or crop.size == 0:
            return None

        results = self.model(crop, conf=self.conf, device=self.device, verbose=False)

        has_helmet = False
        no_helmet = False

        for r in results:
            if r.boxes is None:
                continue
            for cls_id in r.boxes.cls.cpu().numpy():
                name = self.names[int(cls_id)].lower()
                if "no" in name:          # khớp "no_helmet", "no-helmet", "nohelmet"...
                    no_helmet = True
                elif "helmet" in name:
                    has_helmet = True

        if no_helmet:
            return False
        if has_helmet:
            return True
        return None


class HelmetVoteAggregator:
    def __init__(self, window=5, min_no_helmet=3):
        self.window = window
        self.min_no_helmet = min_no_helmet
        self.history = defaultdict(lambda: deque(maxlen=window))
        self.violated_ids = set()

    def update(self, track_id, result):
        if result is None:
            return False

        self.history[track_id].append(result)

        if track_id in self.violated_ids:
            return False

        no_helmet_count = sum(1 for r in self.history[track_id] if r is False)
        if no_helmet_count >= self.min_no_helmet:
            self.violated_ids.add(track_id)
            return True

        return False
