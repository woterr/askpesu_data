import os
import json
from anytree import Node, RenderTree

# consts
POSTS_FILE = "r_pesu_posts.jsonl"
COMMENTS_FILE = "r_pesu_comments.jsonl"
OUTPUT_FOLDER = "processed_posts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
AUTOMOD_TEXT = "While you wait for a response, please take a moment to review some important and helpful resources."


# fncs
def clean_comment(body, author=None):
    if not body or body.lower() in ["[deleted]", "[removed]"]:
        return None
    if author == "AutoModerator":
        return None
    if AUTOMOD_TEXT in body:
        return None
    return body


def build_comment_tree(comment_json, parent_node=None):
    data = comment_json
    body = clean_comment(data.get("body"), author=data.get("author"))
    if not body:
        return None
    node = Node(body, parent=parent_node)
    for reply in data.get("replies", []):
        build_comment_tree(reply, parent_node=node)
    return node


def tree_to_string(root):
    lines = []
    for pre, _, node in RenderTree(root):
        lines.append(f"{pre}{node.name}")
    return "\n".join(lines)


"""
post: has a `name` attribute with an ID
comment: has `link_ID` attribute with the same post ID
comment replies (threads/trees): have `parent_ID` attribute which map to the parent comment
"""


comments_by_post = {}
with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        comment = json.loads(line)
        post_id = comment.get("link_id", "").split("_")[-1]
        if post_id:
            comments_by_post.setdefault(post_id, []).append(comment)

with open(POSTS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        post = json.loads(line)
        post_id = post.get("id")
        if not post_id:
            continue

        post_comments = comments_by_post.get(post_id, [])

        filtered_comments = [
            c
            for c in post_comments
            if clean_comment(c.get("body"), author=c.get("author"))
        ]

        if not filtered_comments:
            continue

        comment_objs = []
        for c in filtered_comments:
            node = build_comment_tree(c)
            if node:
                comment_objs.append({"id": c.get("id"), "body": tree_to_string(node)})

        post_dict = {
            "id": post_id,
            "title": post.get("title", "N/A"),
            "content": post.get("selftext", ""),
            "metadata": {
                "author": post.get("author"),
                "url": post.get("url"),
                "permalink": post.get("permalink"),
                "score": post.get("score"),
                "created_utc": post.get("created_utc"),
                "flair": post.get("link_flair_text"),
                "nsfw": post.get("over_18"),
                "type": "submission",
            },
            "comments": comment_objs,
        }

        out_path = os.path.join(OUTPUT_FOLDER, f"{post_id}.json")
        if not os.path.exists(out_path):
            with open(out_path, "w", encoding="utf-8") as f_out:
                json.dump(post_dict, f_out, indent=2, ensure_ascii=False)
