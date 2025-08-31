import praw
import json
import os
import time
from anytree import Node, RenderTree

# -------------------- CONFIG --------------------
reddit = praw.Reddit(
    client_id="cs1jzzKd_vx2WtBu7syFew",
    client_secret="OVBNie8oPWShlyWQaGn8ugQcl8xP2Q",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
)

SUBREDDIT = "PESU"
DATA_FOLDER = "reddit_data_json"
AUTOMOD_TEXT = "While you wait for a response, please take a moment to review some important and helpful resources."
SLEEP_TIME = 2
BATCH_SIZE = 100  # posts per batch
MAX_RETRIES = 3


# -------------------- HELPERS --------------------
def clean_comment(comment):
    if not comment or comment.body is None:
        return None
    body = comment.body.strip().replace("\n", " ").replace("\r", " ")
    author = str(comment.author) if comment.author else ""
    if not body or body.lower() in ["[deleted]", "[removed]"]:
        return None
    if author == "AutoModerator" or AUTOMOD_TEXT in body:
        return None
    return body


def build_anytree(comment, parent_node=None):
    body = clean_comment(comment)
    if not body:
        return None
    node = Node(body, parent=parent_node)
    replies = [
        r for r in getattr(comment, "replies", []) if isinstance(r, praw.models.Comment)
    ]
    for reply in replies:
        build_anytree(reply, parent_node=node)
    return node


def tree_to_string(root):
    lines = []
    for pre, _, node in RenderTree(root):
        lines.append(f"{pre}{node.name}")
    return "\n".join(lines)


def load_existing_ids(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    ids = set()
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            post_id = filename.replace(".json", "")
            ids.add(post_id)
    print(len(ids), "existing entries found")
    return ids


def get_last_fullname_from_folder(folder_path):
    """Return fullname of the newest post from existing JSON files"""
    if not os.path.exists(folder_path):
        return None
    files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    if not files:
        return None

    files_fullpath = [os.path.join(folder_path, f) for f in files]
    files_fullpath.sort(key=os.path.getctime)  # oldest -> newest
    newest_file = files_fullpath[-1]

    try:
        with open(newest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            post_id = data.get("metadata", {}).get("id")
            if post_id:
                return f"t3_{post_id}"  # fullname format for Reddit API
    except Exception:
        pass
    return None


def save_post_json(submission, thread_strings):
    metadata = {
        "id": submission.id,
        "author": submission.author.name if submission.author else "[deleted]",
        "url": submission.url,
        "permalink": submission.permalink,
        "score": submission.score,
        "upvote_ratio": submission.upvote_ratio,
        "created_utc": submission.created_utc,
        "flair": submission.link_flair_text or "",
        "nsfw": submission.over_18,
    }

    post_dict = {
        "title": submission.title,
        "content": submission.selftext.strip(),
        "metadata": metadata,
        "comments": thread_strings,
    }

    filename = f"{submission.id}.json"
    filepath = os.path.join(DATA_FOLDER, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(post_dict, f, indent=2, ensure_ascii=False)


# -------------------- SCRAPER --------------------
def scrape_subreddit_continuous():
    existing_ids = load_existing_ids(DATA_FOLDER)
    last_fullname = get_last_fullname_from_folder(DATA_FOLDER)
    total_written = 0

    while True:
        try:
            subreddit = reddit.subreddit(SUBREDDIT)
            params = {"after": last_fullname} if last_fullname else {}
            posts = list(subreddit.new(limit=BATCH_SIZE, params=params))

            if not posts:
                print("No new posts found. Sleeping for 60 seconds...")
                time.sleep(60)
                continue

            for submission in posts:
                if submission.id in existing_ids:
                    continue

                retries = 0
                while retries < MAX_RETRIES:
                    try:
                        submission.comments.replace_more(limit=None)
                        break
                    except Exception:
                        retries += 1
                        time.sleep(5)
                else:
                    print(f"Skipping {submission.id} due to repeated errors")
                    continue

                valid_comments = [c for c in submission.comments if clean_comment(c)]
                if not valid_comments:
                    continue

                thread_strings = []
                for comment in submission.comments:
                    if clean_comment(comment):
                        root = build_anytree(comment)
                        thread_strings.append(tree_to_string(root))

                if thread_strings:
                    save_post_json(submission, thread_strings)
                    existing_ids.add(submission.id)
                    total_written += 1
                    print(f"Saved: {submission.id} - {submission.title}")
                    print(f"Total posts saved: {total_written}")
                    time.sleep(SLEEP_TIME)

            # update last_fullname to the newest post in this batch
            last_fullname = posts[-1].name

        except praw.exceptions.APIException as e:
            print(f"Reddit API limit hit: {e}. Sleeping for 60 seconds.")
            time.sleep(60)
        except Exception as e:
            print(f"Unexpected error: {e}. Sleeping for 10 seconds.")
            time.sleep(10)


if __name__ == "__main__":
    scrape_subreddit_continuous()
