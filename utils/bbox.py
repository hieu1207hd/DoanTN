def bbox_overlap_area(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0
    return (ix2 - ix1) * (iy2 - iy1)


def find_best_overlap(target_bbox, candidates):
    best, best_overlap = None, 0
    for c in candidates:
        overlap = bbox_overlap_area(target_bbox, c["bbox"])
        if overlap > best_overlap:
            best_overlap = overlap
            best = c
    return best
