import os
import shutil
import math

INPUT_FOLDER = "reddit_posts_processed"
OUTPUT_FOLDERS = ["1", "2", "3"]

for folder in OUTPUT_FOLDERS:
    os.makedirs(folder, exist_ok=True)

files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".json")]
files.sort()

split_size = math.ceil(len(files) / 3)

for i, folder in enumerate(OUTPUT_FOLDERS):
    start = i * split_size
    end = start + split_size
    for f in files[start:end]:
        src = os.path.join(INPUT_FOLDER, f)
        dst = os.path.join(folder, f)
        shutil.copy(src, dst)
