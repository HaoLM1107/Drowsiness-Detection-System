import cv2
import time
import serial
import threading
import pygame
import requests 
from ultralytics import YOLO

# ================= 1. CẤU HÌNH TELEGRAM (ĐÃ ĐIỀN SẴN) =================
TELEGRAM_TOKEN = "8281327487:AAFAWtv89xz8Ofa__9h-f_kWxnw7yl4wXsM"
TELEGRAM_CHAT_ID = "6227223082" 

# ================= 2. CẤU HÌNH HỆ THỐNG =================
MODEL_PATH = "best.onnx"   
INPUT_SIZE = 320           
CONF_THRESHOLD = 0.45      # <--- Đã trả về mức chuẩn (Khắt khe hơn, ít báo ảo)
IOU_THRESHOLD = 0.45
SOUND_COOLDOWN = 4         
TELEGRAM_COOLDOWN = 10     

# ================= 3. KẾT NỐI PHẦN CỨNG =================
# --- ARDUINO ---
try:
    print(">>> Dang ket noi Arduino...")
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    time.sleep(2) 
    print(">>> ARDUINO: KET NOI THANH CONG!")
except Exception as e:
    print(f"!!! LOI ARDUINO: {e}")
    arduino = None

# --- ÂM THANH ---
try:
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0) # Max Volume
    sounds = {
        "drowsy": "alert_drowsy.mp3",
        "texting_phone": "alert_texting_phone.mp3",
        "talking_phone": "alert_talking_phone.mp3",
        "turning": "alert_turning.mp3"
    }
    print(">>> AM THANH: KHOI TAO THANH CONG!")
except Exception as e:
    print(f"!!! LOI AM THANH: {e}")

last_sound_time = 0
last_telegram_time = 0

# ================= CÁC HÀM XỬ LÝ (CHẠY NGẦM) =================

def send_arduino(signal_char):
    if arduino and arduino.is_open:
        try:
            arduino.write(signal_char.encode())
        except:
            pass

def play_sound_thread(behavior_key):
    global last_sound_time
    current_time = time.time()
    
    if current_time - last_sound_time > SOUND_COOLDOWN:
        if behavior_key in sounds:
            try:
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(sounds[behavior_key])
                    pygame.mixer.music.play()
                    last_sound_time = current_time
            except Exception as e:
                print(f"Loi loa: {e}")

def send_telegram_thread(frame, message):
    global last_telegram_time
    current_time = time.time()

    if current_time - last_telegram_time > TELEGRAM_COOLDOWN:
        try:
            print(f"-> Telegram: Dang gui anh '{message}'...")
            _, img_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            files = {'photo': ('alert.jpg', img_encoded.tobytes())}
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"⚠️ CẢNH BÁO: {message}!"}
            requests.post(url, files=files, data=data)
            last_telegram_time = current_time
            print("-> Telegram: GUI THANH CONG!")
        except Exception as e:
            print(f"!!! Loi Telegram: {e}")

# ================= CHƯƠNG TRÌNH CHÍNH =================
print(f"--- DANG LOAD MODEL: {MODEL_PATH} ---")
try:
    model = YOLO(MODEL_PATH, task='detect')
except:
    print("!!! LOI: Khong tim thay file best.onnx !!!")
    exit()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

print("--- HE THONG SAN SANG! (Nhan 'q' de thoat) ---")

while True:
    ret, frame = cap.read()
    if not ret: break

    results = model(frame, imgsz=INPUT_SIZE, stream=True, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD, verbose=False)
    
    behavior = "awake" 
    
    for r in results:
        frame = r.plot() 
        if len(r.boxes) > 0:
            best = max(r.boxes, key=lambda x: x.conf[0])
            cls_id = int(best.cls[0])
            name = model.names[cls_id]
            if name != "awake":
                behavior = name

    status_text = "TINH TAO (Awake)"
    color = (0, 255, 0) 

    # --- TÌNH HUỐNG 1: NGỦ GẬT ---
    if behavior == "drowsy":
        send_arduino('D') 
        threading.Thread(target=play_sound_thread, args=("drowsy",)).start()
        threading.Thread(target=send_telegram_thread, args=(frame, "TAI XE NGU GAT")).start()
        status_text = "NGU GAT !!!"
        color = (0, 0, 255)

    # --- TÌNH HUỐNG 2: DÙNG ĐIỆN THOẠI / QUAY ĐẦU ---
    elif behavior in ["texting_phone", "talking_phone", "turning"]:
        send_arduino('W') 
        threading.Thread(target=play_sound_thread, args=(behavior,)).start()
        threading.Thread(target=send_telegram_thread, args=(frame, behavior)).start()
        status_text = f"CANH BAO: {behavior}"
        color = (0, 255, 255)

    # --- TÌNH HUỐNG 3: TỈNH TÁO ---
    else:
        send_arduino('O') 

    cv2.putText(frame, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    cv2.imshow("HE THONG CANH BAO (Final)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if arduino: arduino.close()
cv2.destroyAllWindows()