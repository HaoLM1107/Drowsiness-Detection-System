import cv2
from ultralytics import YOLO
from gtts import gTTS
import os
import time
import random
import threading
import requests
import tkinter as tk
from tkinter import ttk
import logging
import queue

import cv2
from ultralytics import YOLO
from gtts import gTTS

import tkinter as tk
from tkinter import ttk

# Hiển thị video trong Tk (không cần cv2.imshow)
from PIL import Image, ImageTk

# ----------------------------
# CONFIG / ENV (KHÔNG HARDCODE TOKEN)
# ----------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

# Tắt logging của ultralytics
logging.getLogger("ultralytics").setLevel(logging.WARNING)

# Load model YOLO
model = YOLO("runs/detect/train3/weights/best.pt")

class_names = {
    0: "awake",
    1: "drowsy",
    2: "texting_phone",
    3: "turning",
    4: "talking_phone",
}

alert_cooldowns = {
    "drowsy": 15,
    "texting_phone": 10,
    "talking_phone": 8,
    "turning": 5,
}

DETECTION_DURATION_THRESHOLD = 3

detection_start_times = {k: None for k in alert_cooldowns.keys()}
last_alert_times = {k: 0 for k in alert_cooldowns.keys()}
detection_counts = {k: 0 for k in alert_cooldowns.keys()}

alert_messages = {
    "drowsy": [
        "Bạn có mệt không? Cần dừng lại nghỉ ngơi không?",
        "Tình trạng buồn ngủ phát hiện! Bạn cần tập trung!",
        "Hệ thống phát hiện mệt mỏi, đề nghị nghỉ ngơi!",
        "Buồn ngủ rồi à? Hay mình tìm chỗ nghỉ một chút nhé!",
        "Mắt bạn có vẻ nặng rồi, nghỉ chút cho tỉnh táo nào!",
        "Bạn có muốn dừng lại uống cà phê không? Nói 'có' nếu muốn nhé!",
    ],
    "texting_phone": [
        "Bạn ơi, nguy hiểm lắm! Đừng nhắn tin khi lái xe!",
        "Việc nhắn tin có thể đợi, tập trung lái xe bạn nhé!",
        "Nguy hiểm! Xin đừng sử dụng điện thoại!",
        "Điện thoại quan trọng, nhưng an toàn còn hơn, bạn nhé!",
        "Nhắn tin bây giờ là đánh cược mạng sống đấy bạn ơi!",
        "Tin nhắn không chạy mất đâu, để yên cho mình lái xe nào!",
    ],
    "talking_phone": [
        "Bạn vui lòng dùng tai nghe để đàm thoại an toàn!",
        "Trò chuyện điện thoại làm giảm tập trung lái xe!",
        "Xin hãy dừng xe nếu cần gọi điện khẩn cấp!",
        "Nói chuyện sau cũng được mà, giờ tập trung lái xe nhé bạn!",
        "Dùng tai nghe đi bạn, vừa an toàn vừa tiện!",
        "Cuộc gọi quan trọng thì dừng xe đã, đừng mạo hiểm!",
    ],
    "turning": [
        "Chú ý quan sát trước khi chuyển hướng!",
        "Xin bật xi-nhan trước khi rẽ!",
        "Giảm tốc độ khi vào cua bạn nhé!",
        "Quan sát gương chiếu hậu trước khi rẽ, bạn nhớ nhé!",
        "Cẩn thận xe phía sau khi chuyển hướng nha bạn!",
        "Xi-nhan bật chưa bạn? Rẽ từ từ thôi!",
    ],
}


def send_video_to_telegram(file_path: str, class_name: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Bỏ qua Telegram: thiếu TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (env).")
        try:
            os.remove(file_path)
        except:
            pass
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        with open(file_path, "rb") as video_file:
            files = {"video": video_file}
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": f"Phát hiện hành vi: {class_name} lúc {time.strftime('%H:%M:%S %d/%m/%Y')}",
            }
            response = requests.post(url, files=files, data=data, timeout=60)

        if response.status_code == 200:
            print(f"Đã gửi video {file_path} đến Telegram.")
        else:
            print(f"Lỗi gửi video Telegram: {response.status_code} | {response.text}")

        os.remove(file_path)
    except Exception as e:
        print(f"Lỗi khi gửi video qua Telegram: {e}")
        try:
            os.remove(file_path)
        except:
            pass


def speak_alert(message: str):
    try:
        print("ALERT:", message)
        tts = gTTS(text=message, lang="vi", slow=False)
        tts.save("alert.mp3")
        from playsound import playsound  # pip install playsound==1.2.2

        playsound("alert.mp3")
        os.remove("alert.mp3")
    except Exception as e:
        print(f"Lỗi khi phát âm thanh: {e}")


def get_time_context():
    hour = time.localtime().tm_hour
    if 5 <= hour < 12:
        return "sáng"
    if 12 <= hour < 17:
        return "chiều"
    if 17 <= hour < 22:
        return "tối"
    return "đêm"


def get_weather_data(lat=21.0278, lon=105.8342):
    if not OPENWEATHER_API_KEY:
        return "unknown", 25, "Unknown"

    url = (
        f"http://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    )
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        weather = data["weather"][0]["main"].lower()
        temp = data["main"]["temp"]
        city = data["name"]
        return weather, temp, city
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu thời tiết: {e}")
        return "unknown", 25, "Unknown"


def get_weather_alert(class_name, weather, temp, time_context):
    weather_messages = {
        "rain": "Trời đang mưa, bạn cẩn thận đường trơn nhé!",
        "fog": "Sương mù dày đặc, bạn giảm tốc độ và bật đèn đi nhé!",
        "clear": "Trời quang đãng, nhưng bạn vẫn cần tập trung!",
        "clouds": "Trời nhiều mây, chú ý tầm nhìn hạn chế nha bạn!",
    }
    temp_messages = {
        "hot": "Trời nóng quá, bạn nhớ uống nước để tỉnh táo nhé!",
        "cold": "Trời lạnh rồi, bạn giữ ấm để lái xe an toàn!",
    }

    base_message = random.choice(alert_messages[class_name])
    weather_message = weather_messages.get(weather, "")
    temp_message = temp_messages["hot"] if temp > 30 else temp_messages["cold"] if temp < 15 else ""

    if random.random() < 0.5:
        if weather_message and temp_message:
            return f"Buổi {time_context} {weather_message} {temp_message} {base_message}"
        if weather_message:
            return f"Buổi {time_context} {weather_message} {base_message}"
        return f"Buổi {time_context} mà {base_message}"
    return base_message


# ----------------------------
# CAMERA + RECORDING (DÙNG LOCK TRÁNH CAP READ ĐỤNG NHAU)
# ----------------------------
cap = cv2.VideoCapture(0)
cap_lock = threading.Lock()


def record_video(class_name: str, seconds: int = 15, fps: float = 20.0):
    # Ghi trực tiếp từ camera. Vì dùng cùng cap => khóa cap_lock.
    if not cap.isOpened():
        return

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_path = f"record_{class_name}_{timestamp}.avi"
    fourcc = cv2.VideoWriter_fourcc(*"XVID")

    # Lấy 1 frame để biết size
    with cap_lock:
        ret, frame0 = cap.read()
    if not ret or frame0 is None:
        return

    h, w = frame0.shape[:2]
    out = cv2.VideoWriter(file_path, fourcc, fps, (w, h))

    start = time.time()
    while time.time() - start < seconds:
        with cap_lock:
            ret, fr = cap.read()
        if ret and fr is not None:
            out.write(fr)
        time.sleep(1.0 / fps)

    out.release()
    print(f"Đã ghi video: {file_path}")

    if class_name == "drowsy":
        threading.Thread(target=send_video_to_telegram, args=(file_path, class_name), daemon=True).start()
    else:
        # không gửi thì xóa luôn để khỏi đầy ổ
        try:
            os.remove(file_path)
        except:
            pass


# ----------------------------
# GUI
# ----------------------------
root = tk.Tk()
root.title("Driver Monitoring System")
root.geometry("720x520")
root.resizable(False, False)

status_label = ttk.Label(root, text="Trạng thái: Đang chạy", font=("Arial", 12))
status_label.pack(pady=6)

behavior_label = ttk.Label(root, text="Hành vi: Chưa phát hiện", font=("Arial", 11))
behavior_label.pack(pady=4)

weather_label = ttk.Label(root, text="Thời tiết: Đang cập nhật", font=("Arial", 11))
weather_label.pack(pady=2)

location_label = ttk.Label(root, text="Địa điểm: Đang cập nhật", font=("Arial", 11))
location_label.pack(pady=2)

time_label = ttk.Label(root, text="Thời gian: Đang cập nhật", font=("Arial", 11))
time_label.pack(pady=2)

driving_time_label = ttk.Label(root, text="Thời gian lái: 0 phút", font=("Arial", 11))
driving_time_label.pack(pady=2)

video_label = ttk.Label(root)
video_label.pack(pady=10)


def update_gui(behavior, weather, temp, city, current_time_str, driving_time):
    behavior_label.config(text=f"Hành vi: {behavior}")
    if behavior == "awake":
        behavior_label.config(foreground="green")
    elif behavior in alert_cooldowns:
        behavior_label.config(foreground="red")
    else:
        behavior_label.config(foreground="black")

    weather_label.config(text=f"Thời tiết: {weather}, {temp}°C")
    location_label.config(text=f"Địa điểm: {city}")
    time_label.config(text=f"Thời gian: {current_time_str}")
    driving_time_label.config(text=f"Thời gian lái: {driving_time:.0f} phút")


# ----------------------------
# WORKER THREAD + UI QUEUE
# ----------------------------
start_time = time.time()

last_weather_update = 0
weather_update_interval = 300
current_weather, current_temp, current_city = "unknown", 25, "Unknown"

ui_q = queue.Queue(maxsize=1)
stop_event = threading.Event()


def worker_vision():
    global last_weather_update, current_weather, current_temp, current_city

    while not stop_event.is_set() and cap.isOpened():
        with cap_lock:
            ret, frame = cap.read()
        if not ret or frame is None:
            break

        results = model(frame, conf=0.65, verbose=False)
        annotated_frame = results[0].plot()

        now = time.time()
        driving_time = (now - start_time) / 60.0

        if now - last_weather_update > weather_update_interval:
            current_weather, current_temp, current_city = get_weather_data(lat=21.0278, lon=105.8342)
            last_weather_update = now
            print(f"Địa điểm: {current_city}, Thời tiết: {current_weather}, Nhiệt độ: {current_temp}°C")

        detected_classes = set()
        for box in results[0].boxes:
            class_id = int(box.cls)
            detected_classes.add(class_names.get(class_id, "unknown"))

        time_context = get_time_context()
        detected_behavior = "Chưa phát hiện"
        if detected_classes:
            detected_behavior = list(detected_classes)[0]

        # cảnh báo
        for cname in alert_cooldowns:
            if cname in detected_classes:
                if detection_start_times[cname] is None:
                    detection_start_times[cname] = now
                else:
                    elapsed = now - detection_start_times[cname]
                    if elapsed >= DETECTION_DURATION_THRESHOLD:
                        cooldown = alert_cooldowns[cname]
                        last_time = last_alert_times[cname]
                        if now - last_time > cooldown:
                            detection_counts[cname] += 1
                            msg = get_weather_alert(cname, current_weather, current_temp, time_context)
                            if detection_counts[cname] > 3:
                                msg = f"Bạn ơi, lần này là lần thứ {detection_counts[cname]} rồi! {msg}"

                            threading.Thread(target=speak_alert, args=(msg,), daemon=True).start()
                            threading.Thread(target=record_video, args=(cname,), daemon=True).start()

                            last_alert_times[cname] = now
                            detection_start_times[cname] = None
            else:
                detection_start_times[cname] = None

        # overlay text
        current_time_str = time.strftime("%H:%M:%S %d/%m/%Y")
        cv2.putText(annotated_frame, current_time_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(
            annotated_frame,
            f"Dia diem: {current_city}",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            annotated_frame,
            f"Thoi tiet: {current_weather}, {current_temp}°C",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )

        payload = (detected_behavior, current_weather, current_temp, current_city, current_time_str, driving_time, annotated_frame)

        try:
            if ui_q.full():
                ui_q.get_nowait()
            ui_q.put_nowait(payload)
        except:
            pass

    stop_event.set()


def ui_loop():
    try:
        behavior, weather, temp, city, current_time_str, driving_time, frame = ui_q.get_nowait()
        update_gui(behavior, weather, temp, city, current_time_str, driving_time)

        # BGR -> RGB -> Tk image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img = img.resize((680, 380))
        imgtk = ImageTk.PhotoImage(image=img)
        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
    except queue.Empty:
        pass

    if not stop_event.is_set():
        root.after(15, ui_loop)


def on_close():
    stop_event.set()
    try:
        time.sleep(0.1)
    except:
        pass
    try:
        if cap.isOpened():
            cap.release()
    except:
        pass
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

threading.Thread(target=worker_vision, daemon=True).start()
root.after(0, ui_loop)
root.mainloop()
