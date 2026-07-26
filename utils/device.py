import torch


def resolve_device(device):
    """"auto" -> 0 (GPU đầu tiên) nếu máy có CUDA, "cpu" nếu không. Giá trị
    khác ("cpu", 0, 1...) giữ nguyên, không đổi.

    Dùng CHUNG cho Tracker/HelmetDetector/PlateDetector để đảm bảo TẤT CẢ
    model trong hệ thống chạy cùng 1 thiết bị theo config.DEVICE. Bản gốc
    chỉ Tracker tự resolve device - HelmetDetector/PlateDetector không nhận
    tham số device, luôn để mặc định của ultralytics tự chọn -> nếu máy có
    GPU nhưng driver/CUDA không nhận diện được lúc model tự chọn, model đó
    âm thầm rơi về CPU trong khi Tracker vẫn chạy GPU, làm chậm cả pipeline
    một cách khó phát hiện (FPS thấp mà không rõ nguyên nhân).
    """
    if device == "auto":
        return 0 if torch.cuda.is_available() else "cpu"
    return device
