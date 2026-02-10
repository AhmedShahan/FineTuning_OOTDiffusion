######### MOVE ALL THE DATA from SOURCE ---- TARGET FOLDER

# import os
# import shutil

# source_dir = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/scraped_data/pinterest_jubba"
# target_dir = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/all_data/jubba"

# os.makedirs(target_dir, exist_ok=True)

# image_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")

# for filename in os.listdir(source_dir):
#     if filename.lower().endswith(image_extensions):
#         src_path = os.path.join(source_dir, filename)
#         dst_path = os.path.join(target_dir, filename)
#         shutil.move(src_path, dst_path)

# print("All images moved successfully.")


### ================== IMAGE TYPE AND TOTAL IMAGE =========================== ##
# import os
# from collections import Counter

# folder_path = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/all_data/jubba"

# image_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")

# total_images = 0
# extension_count = Counter()

# for filename in os.listdir(folder_path):
#     if filename.lower().endswith(image_extensions):
#         total_images += 1
#         ext = os.path.splitext(filename)[1].lower()
#         extension_count[ext] += 1

# print(f"Total images: {total_images}\n")
# print("Image types:")
# for ext, count in extension_count.items():
#     print(f"{ext} : {count}")



##############
# import os
# from PIL import Image

# folder_path = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/all_data/jubba"

# image_extensions = (".png", ".jpeg", ".bmp", ".tiff", ".webp")

# for filename in os.listdir(folder_path):
#     if filename.lower().endswith(image_extensions):
#         img_path = os.path.join(folder_path, filename)

#         with Image.open(img_path) as img:
#             img = img.convert("RGB")
#             new_path = os.path.join(
#                 folder_path,
#                 os.path.splitext(filename)[0] + ".jpg"
#             )
#             img.save(new_path, "JPEG", quality=95)

#         os.remove(img_path)  # remove original file

# print("Conversion completed and originals removed.")



############# RENAME
import os

# Path to your folder containing images
folder_path = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/all_data/jubba"

# Get list of all files in the folder
files = os.listdir(folder_path)

# Filter image files (you can add more extensions if needed)
image_extensions = (".jpg", ".jpeg", ".png", ".webp")
images = [f for f in files if f.lower().endswith(image_extensions)]

# Sort images (optional, based on name)
images.sort()

# Rename images
for idx, image_name in enumerate(images, start=1):
    ext = os.path.splitext(image_name)[1]  # Get original extension
    new_name = f"jubba_{idx}{ext}"
    old_path = os.path.join(folder_path, image_name)
    new_path = os.path.join(folder_path, new_name)
    os.rename(old_path, new_path)
    print(f"Renamed {image_name} -> {new_name}")

print("All images renamed successfully!")
