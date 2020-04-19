import json

with open('test.json') as f:
    data = json.load(f)

obj = {}
obj['items'] = data

print(obj)
