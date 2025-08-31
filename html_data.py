import requests
import json
import os
import time
from anytree import Node, RenderTree

# -------------------- CONFIG --------------------
headers = {"User-agent": "Mozilla/5.0"}
subreddit = input("Enter subreddit: ")
DATA_FOLDER = "reddit_data_json_html"
os.makedirs(DATA_FOLDER, exist_ok=True)

AUTOMOD_TEXT = "While you wait for a response, please take a moment to review some important and helpful resources."
MAX_RETRIES = 5
SLEEP_TIME = 2

# Choose sort: "hot", "new", "top", "rising"
POST_SORT = "rising"
TIME_FILTER = (
    "all"  # only used if POST_SORT="top"; options: hour, day, week, month, year, all
)
LIMIT = 50  # posts per request


# -------------------- HELPERS --------------------
def clean_comment(body, author=None):
    if not body or body.lower() in ["[deleted]", "[removed]"]:
        return None
    if author == "AutoModerator":
        return None
    if AUTOMOD_TEXT in body:
        return None
    return body


def build_comment_tree(comment_json, parent_node=None):
    data = comment_json.get("data", {})
    body = clean_comment(data.get("body"), author=data.get("author"))
    if not body:
        return None
    node = Node(body, parent=parent_node)

    replies = data.get("replies")
    if replies and isinstance(replies, dict):
        children = replies.get("data", {}).get("children", [])
        for child in children:
            if child.get("kind") == "t1":
                build_comment_tree(child, parent_node=node)
    return node


def tree_to_string(root):
    lines = []
    for pre, _, node in RenderTree(root):
        lines.append(f"{pre}{node.name}")
    return "\n".join(lines)


def fetch_post_comments(post_id):
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 429:
                print("Rate limited. Sleeping 60s...")
                time.sleep(60)
                continue
            if r.status_code != 200:
                print(
                    f"Failed to fetch comments for {post_id}, status: {r.status_code}"
                )
                return []
            comment_jsons = r.json()[1]["data"]["children"]
            trees = []
            for c in comment_jsons:
                if c.get("kind") == "t1":
                    node = build_comment_tree(c)
                    if node:
                        trees.append(node)
            return trees
        except Exception as e:
            print(f"Error fetching comments for {post_id}: {e}")
            time.sleep(5)
    return []


def scrape_subreddit_posts(sort=POST_SORT, time_filter=TIME_FILTER, limit=LIMIT):
    after = None
    count = 0
    existing_ids = set(f.replace(".json", "") for f in os.listdir(DATA_FOLDER))

    while True:
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
        if sort == "top" and time_filter:
            url += f"&t={time_filter}"
        if after:
            url += f"&after={after}"

        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 429:
                    print("Rate limited. Sleeping 60s...")
                    time.sleep(60)
                    continue
                if r.status_code != 200:
                    print(f"Failed to fetch posts, status: {r.status_code}")
                    time.sleep(5)
                    continue
                data = r.json()["data"]
                break
            except Exception as e:
                print(f"Error fetching posts: {e}. Retrying...")
                time.sleep(5)
        else:
            print("Failed after multiple attempts, exiting loop.")
            break

        after = data.get("after")
        for post in data.get("children", []):
            post_data = post["data"]
            post_id = post_data["id"]
            if post_id in existing_ids:
                continue

            post_title = post_data["title"]
            post_url = post_data["url"]

            print(f"Fetching comments for post: {post_id} - {post_title}")
            comment_trees = fetch_post_comments(post_id)

            post_dict = {
                "title": post_title,
                "content": post_data.get("selftext", ""),
                "metadata": {
                    "id": post_id,
                    "author": post_data.get("author"),
                    "url": post_url,
                    "permalink": post_data.get("permalink"),
                    "score": post_data.get("score"),
                    "upvote_ratio": post_data.get("upvote_ratio"),
                    "created_utc": post_data.get("created_utc"),
                    "flair": post_data.get("link_flair_text"),
                    "nsfw": post_data.get("over_18"),
                },
                "comments": [tree_to_string(t) for t in comment_trees],
            }

            with open(
                os.path.join(DATA_FOLDER, f"{post_id}.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(post_dict, f, indent=2, ensure_ascii=False)

            existing_ids.add(post_id)
            count += 1
            time.sleep(SLEEP_TIME)

        if not after:
            break
    print(f"Scraped {count} posts.")


if __name__ == "__main__":
    scrape_subreddit_posts()
