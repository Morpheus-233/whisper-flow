import json

with open("data/calibration_sentences.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total count: {len(data)}")
cats = {}
for idx, d in enumerate(data):
    cat = d.get("category")
    cats[cat] = cats.get(cat, 0) + 1
    assert "id" in d and "text" in d and "phonetic_keywords" in d
    assert len(d["phonetic_keywords"]) > 0
    assert d["id"] == idx + 1

print(f"Categories: {cats}")
print(f"Sample #1 ({data[0]['category']}): {data[0]['text']} -> keywords: {data[0]['phonetic_keywords']}")
print(f"Sample #51 ({data[50]['category']}): {data[50]['text']} -> keywords: {data[50]['phonetic_keywords']}")
print(f"Sample #100 ({data[99]['category']}): {data[99]['text']} -> keywords: {data[99]['phonetic_keywords']}")
