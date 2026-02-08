import os
from PIL import Image

input_dir = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/data_raw/webp_images"
output_dir = "/media/shahanahmed/c229a233-ed4f-4f67-9e09-5890e65956f7/FineTuning_OOTDiffusion/data_raw/jpg_images"

os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.lower().endswith(".webp"):
        base_name = os.path.splitext(filename)[0]  # jubba_23
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, base_name + ".jpg")

        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                bg.save(output_path, "JPEG", quality=95)
            else:
                img.convert("RGB").save(output_path, "JPEG", quality=95)

        print(f"Converted: {filename} -> {base_name}.jpg")
