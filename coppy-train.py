import os
import shutil
import random

# ====== SỬA ĐÚNG ĐƯỜNG DẪN ======
base_dir = r"C:\Users\LENOVO\Documents\YOLO-Based-Drowsiness-Detection-System-for-Road-Safety-main-main\data3"

train_images = os.path.join(base_dir, "train/images")
train_labels = os.path.join(base_dir, "train/labels")

val_images = os.path.join(base_dir, "val/images")
val_labels = os.path.join(base_dir, "val/labels")

NUM_VAL = 10  # số ảnh cần copy sang val

# ====== TẠO THƯ MỤC VAL NẾU CHƯA CÓ ======
os.makedirs(val_images, exist_ok=True)
os.makedirs(val_labels, exist_ok=True)

# ====== LẤY DANH SÁCH ẢNH ======
images = [f for f in os.listdir(train_images)
          if f.lower().endswith(('.jpg', '.png', '.jpeg'))]

assert len(images) >= NUM_VAL, "❌ Không đủ ảnh trong train"

# random ảnh
selected_images = random.sample(images, NUM_VAL)

# ====== COPY ẢNH + LABEL ======
for img in selected_images:
    name = os.path.splitext(img)[0]

    src_img = os.path.join(train_images, img)
    src_lbl = os.path.join(train_labels, name + ".txt")

    dst_img = os.path.join(val_images, img)
    dst_lbl = os.path.join(val_labels, name + ".txt")

    shutil.copy(src_img, dst_img)

    if os.path.exists(src_lbl):
        shutil.copy(src_lbl, dst_lbl)
    else:
        # nếu thiếu label → tạo file rỗng (chuẩn YOLO)
        open(dst_lbl, "w").close()

print(f"✅ Đã copy {NUM_VAL} ảnh + label từ train sang val")
