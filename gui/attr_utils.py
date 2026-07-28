def set_nested_attr(obj, attr_path, value):
    """vd attr_path='tracker.vehicle_conf' -> obj.tracker.vehicle_conf = value.

    Dùng chung cho MỌI cơ chế "chỉnh trực tiếp lúc đang chạy" trong GUI -
    slider conf (ControlPanel) và kéo-chọn ROI trên video (ROIPanel) đều gọi
    hàm này để áp dụng giá trị mới NGAY vào channel đang chạy, không cần
    dừng/khởi động lại.

    Bỏ qua êm (không raise) nếu attribute cấp giữa chưa sẵn sàng - vd channel
    vừa start, _run() chưa kịp khởi tạo tracker/checker/detector trong vài
    chục ms đầu, hoặc người dùng bấm "Kéo chọn ROI" trước khi bấm "Bắt đầu".

    Trả về True nếu đã set thành công, False nếu bỏ qua (không tìm thấy
    attribute cấp giữa) - để nơi gọi (vd ROIPanel) báo đúng trạng thái cho
    người dùng thay vì LUÔN hiện "đã áp dụng" ngay cả khi thực ra không set
    được gì.
    """
    parts = attr_path.split(".")
    target = obj
    try:
        for p in parts[:-1]:
            target = getattr(target, p)
            if target is None:
                return False
        setattr(target, parts[-1], value)
        return True
    except AttributeError:
        return False
