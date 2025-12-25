from ultralytics import YOLO

# 1. Load model (Sử dụng model Nano cho nhẹ và nhanh, phù hợp nhúng Pi 5 sau này)
model = YOLO('yolov8n.pt') 

if __name__ == '__main__':
    # 2. Bắt đầu Train
    results = model.train(
        # --- QUẢN LÝ DỮ LIỆU ---
        data='dataset.yaml',    # File cấu hình bạn vừa sửa (trỏ vào data5)
        epochs=100,             # Chạy 100 vòng
        imgsz=640,              # Kích thước ảnh chuẩn
        batch=16,               # Số ảnh nạp vào RAM mỗi lần (16 là an toàn cho VRAM)

        # --- CẤU HÌNH PHẦN CỨNG (RTX 4060) ---
        device=0,               # Chạy trên Card màn hình rời
        workers=2,              # Số luồng xử lý dữ liệu (Windows nên để thấp để tránh lỗi)
        
        # --- CẤU HÌNH FIX LỖI "AWAKE" & TỐI ƯU ---
        augment=True,           # Để YOLO tự động tăng cường ảnh thông minh
        val=True,               # Kiểm tra chất lượng sau mỗi vòng lặp
        
        # Các thông số biến đổi ảnh (Augmentation):
        flipud=0.0,             # QUAN TRỌNG: Tắt lật dọc (vì tài xế không lái xe ngược đầu)
        fliplr=0.5,             # Lật ngang 50% (mô phỏng vô lăng bên trái/phải)
        mixup=0.0,              # Không trộn 2 ảnh làm 1 (tránh làm rối model lúc này)
        degrees=5.0,            # Chỉ xoay nhẹ ảnh tối đa 5 độ (nghiêng đầu nhẹ)
        
        # --- LƯU KẾT QUẢ ---
        save=True,              # Lưu lại model tốt nhất (best.pt)
        project='runs/detect',  # Thư mục chứa kết quả
        # name='...'            # ĐÃ XÓA: Để nó tự động tạo train8, train9...
    )

    # 3. Xuất model ra định dạng ONNX (Để sau này chạy trên Raspberry Pi cho nhẹ)
    success = model.export(format='onnx')