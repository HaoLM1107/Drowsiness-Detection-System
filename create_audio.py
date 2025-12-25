from gtts import gTTS
import os

print("--- DANG KET NOI GOOGLE DE TAO GIONG NOI ---")

# Danh sách câu cảnh báo (Nội dung ngắn gọn, súc tích)
warnings = {
    "drowsy": "Cảnh báo! Bạn đang buồn ngủ. Vui lòng tỉnh táo!",
    "texting_phone": "Nhắc nhở! Không nhắn tin khi lái xe.",
    "talking_phone": "Nhắc nhở! Không nghe điện thoại khi lái xe.",
    "turning": "Chú ý! Vui lòng nhìn thẳng phía trước."
}

# Vòng lặp tạo file
for key, text in warnings.items():
    filename = f"alert_{key}.mp3"
    print(f"-> Dang tao file: {filename}...")
    
    # lang='vi' là giọng tiếng Việt
    tts = gTTS(text=text, lang='vi') 
    tts.save(filename)

print("\n>>> THANH CONG! DA CO DU 4 FILE CANH BAO.")