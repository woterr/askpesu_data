import os
import json

FOLDER = "reddit_posts_processed"

total_threads = 0
comment_ids = []

for filename in os.listdir(FOLDER):
    filepath = os.path.join(FOLDER, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        post = json.load(f)
        comments_list = post.get("comments", [])
        for comment in comments_list:
            comment_ids.append(comment["id"])
        total_threads += len(comments_list)

print(total_threads)
print(comment_ids)
