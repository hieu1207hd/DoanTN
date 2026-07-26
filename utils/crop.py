def crop_head(frame, x1, y1, x2, y2, head_ratio=0.4):
    h = y2 - y1
    y_head_end = y1 + int(h * head_ratio)
    return frame[y1:y_head_end, x1:x2]
