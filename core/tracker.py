from ultralytics import YOLO

from utils.device import resolve_device


class Tracker:
    def __init__(self, model_path, allowed_classes=(2, 3), context_classes=(), device="auto",
                 conf=0.5, context_conf=None):
        self.model = YOLO(model_path)
        self.allowed_classes = set(allowed_classes)
        # context_classes: các class KHÔNG cần track ID bền (không đếm, không
        # lưu lịch sử) nhưng cần vị trí mỗi frame để đối chiếu, vd class
        # "person" (id=0) dùng để tìm người đang ngồi trên 1 xe cụ thể.
        self.context_classes = set(context_classes)
        self.vehicle_conf = conf
        # Bỏ sót 1 person (miss) nguy hiểm hơn detect dư (person là "context",
        # không tự tạo vi phạm) -> mặc định context_conf THẤP HƠN vehicle_conf,
        # trừ khi người dùng chỉ định khác. Đã quan sát thực tế: xe gần camera
        # nhất (to nhất khung hình) đôi khi bị model bỏ sót person ở ngưỡng
        # conf mặc định dùng chung cho xe.
        self.context_conf = context_conf if context_conf is not None else conf
        # LƯU Ý: vehicle_conf/context_conf là attribute public, có thể bị GUI
        # (hoặc code ngoài) đổi giá trị bất kỳ lúc nào để chỉnh conf khi đang
        # chạy (live-tuning) - KHÔNG cache base_conf ở đây, phải tính lại mỗi
        # lần track() để nhận được giá trị mới nhất.
        self.device = resolve_device(device)

    def track(self, frame):
        # .track() chỉ nhận 1 ngưỡng conf chung -> truyền ngưỡng THẤP NHẤT để
        # không bỏ sót box nào ở tầng model, rồi tự lọc lại chính xác theo
        # từng class bằng conf thật của từng box bên dưới. Tính MỚI mỗi lần
        # gọi (không cache) để phản ánh đúng giá trị hiện tại nếu bị đổi live.
        base_conf = min(self.vehicle_conf, self.context_conf)
        results = self.model.track(
            frame,
            persist=True,
            conf=base_conf,
            device=self.device,
            verbose=False,
        )

        tracks = []
        context = []

        for r in results:
            if r.boxes is None or r.boxes.id is None:
                # r.boxes.id là None khi tracker chưa gán được ID cho frame này
                continue

            boxes = r.boxes.xyxy.cpu().numpy()
            ids = r.boxes.id.cpu().numpy()
            classes = r.boxes.cls.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()

            for box, obj_id, cls, cf in zip(boxes, ids, classes, confs):
                cls = int(cls)
                x1, y1, x2, y2 = map(int, box)

                if cls in self.allowed_classes and cf >= self.vehicle_conf:
                    tracks.append({
                        "id": int(obj_id),
                        "bbox": (x1, y1, x2, y2),
                        "class_id": cls,
                    })
                elif cls in self.context_classes and cf >= self.context_conf:
                    context.append({
                        "id": int(obj_id),
                        "bbox": (x1, y1, x2, y2),
                        "class_id": cls,
                    })

        return tracks, context
