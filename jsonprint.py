import json


with open("reddit_data_json/1n453gk.json", "r") as file:
    data = json.load(file)

print(data["comments"][0])
