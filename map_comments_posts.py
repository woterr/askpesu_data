import json
import os
from anytree import Node, RenderTree

# cnfg
POSTS_FILE = "r_pesu_posts.jsonl"
COMMENTS_FILE = "r_pesu_comments.jsonl"
OUTPUT_FOLDER = "reddit_posts_processed"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
AUTOMOD_TEXT = "While you wait for a response, please take a moment to review some important and helpful resources."


# fncs
def clean_comment(body):
    if not body or body.lower() in ["[deleted]", "[removed]"]:
        return None
    if AUTOMOD_TEXT in body:
        return None
    return body


def build_comment_tree(comment, children_map, parent_node=None):
    text = clean_comment(comment.get("body"))
    if not text:
        return None
    node = Node(text, parent=parent_node)
    for child_id in children_map.get(comment["id"], []):
        child_comment = child_map[child_id]
        build_comment_tree(child_comment, children_map, parent_node=node)
    return node


def tree_to_string(root):
    lines = []
    for pre, _, node in RenderTree(root):
        lines.append(f"{pre}{node.name}")
    return "\n".join(lines)


posts = {}
with open(POSTS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        post = json.loads(line)
        posts[post["id"]] = post

comments = []
with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        comments.append(json.loads(line))

child_map = {c["id"]: c for c in comments}

children_map = {}
for c in comments:
    parent_id = c.get("parent_id", "")
    if parent_id.startswith("t1_"):
        pid = parent_id[3:]
    elif parent_id.startswith("t3_"):
        pid = parent_id[3:]
    else:
        pid = parent_id
    children_map.setdefault(pid, []).append(c["id"])

for post_id, post in posts.items():
    root_comments = []
    for c in comments:
        link_id = c.get("link_id", "")
        if link_id.endswith(post_id) and c.get("parent_id", "").startswith("t3_"):
            root_comments.append(c)

    if not root_comments:
        continue

    comment_objs = []
    for root in root_comments:
        tree_root = build_comment_tree(root, children_map)
        if tree_root:
            comment_objs.append({"id": root["id"], "body": tree_to_string(tree_root)})

    if not comment_objs:
        continue

    output = {
        "id": post_id,
        "title": post.get("title", ""),
        "content": post.get("selftext", ""),
        "metadata": {
            "root_comment_id": root_comments[0]["id"] if root_comments else None,
            "post_id": post_id,
            "author": post.get("author"),
            "url": post.get("url"),
            "permalink": "https://reddit.com" + post.get("permalink", ""),
            "score": post.get("score"),
            "upvote_ratio": post.get("upvote_ratio"),
            "created_utc": post.get("created_utc"),
            "flair": post.get("link_flair_text"),
            "nsfw": post.get("over_18"),
        },
        "comments": comment_objs,
    }

    with open(
        os.path.join(OUTPUT_FOLDER, f"{post_id}.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

print(f"{len(os.listdir(OUTPUT_FOLDER))}")
