class TrafficFlow:
    def __init__(self, line_y, direction="up"):
        self.line_y = line_y
        self.direction = direction

        self.counted_ids = set()
        self.prev_positions = {}

        self.total = 0
        self.car_count = 0
        self.bike_count = 0

    def _crossed_line(self, prev_y, cy):
        if self.direction == "up":
            return prev_y > self.line_y >= cy
        if self.direction == "down":
            return prev_y < self.line_y <= cy
        raise ValueError(f"direction không hợp lệ: {self.direction}")

    def update(self, tracks):
        for obj in tracks:
            obj_id = obj["id"]
            x1, y1, x2, y2 = obj["bbox"]
            cls = obj["class_id"]
            cy = (y1 + y2) // 2

            prev_y = self.prev_positions.get(obj_id)
            self.prev_positions[obj_id] = cy

            if prev_y is None:
                continue

            if self._crossed_line(prev_y, cy) and obj_id not in self.counted_ids:
                self.counted_ids.add(obj_id)
                self.total += 1

                if cls == 2:
                    self.car_count += 1
                elif cls == 3:
                    self.bike_count += 1
