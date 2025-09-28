import os
import json

FOLDER = "reddit_posts_processed"

total_threads = 0

for filename in os.listdir(FOLDER):
    filepath = os.path.join(FOLDER, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        post = json.load(f)
        total_threads += len(post.get("comments", []))

print(total_threads)
