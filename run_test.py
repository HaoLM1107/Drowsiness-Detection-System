from ultralytics import YOLO
import cv2

# 1. Load model "thần thánh" vừa train xong
# Lưu ý: Sửa đường dẫn nếu tên folder của bạn khác train8
model = YOLO('runs/detect/train8/weights/best.pt') 

# 2. Mở Webcam (số 0 là webcam laptop, nếu cắm cam rời thì thử số 1)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # 3. Nhận diện
    # conf=0.5 nghĩa là chắc chắn trên 50% mới hiện khung
    results = model.predict(frame, conf=0.5, imgsz=640, verbose=False)

    # 4. Vẽ khung lên hình
    annotated_frame = results[0].plot()

    # 5. Hiện lên màn hình
    cv2.imshow("TEST DO AN - Hào Le", annotated_frame)

    # Bấm nút 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()