"""
One-off script: exercises the real HTTP API end-to-end -
create exam -> create batch -> upload a real sheet -> check result.
"""
import httpx

BASE = "http://127.0.0.1:8000/api/v1"

# placeholder answer key - all "A" - just to prove the pipeline runs;
# swap in the real key once you have it from your supervisor
answer_key = [{"question": i, "correct_option": "A"} for i in range(1, 201)]

resp = httpx.post(f"{BASE}/exams", json={
    "title": "Ambition Guru Mock Test - pipeline test",
    "template_version": "ambition-guru-v1",
    "answer_key": answer_key,
    "scoring_policy": {
        "points_correct": 1,
        "points_incorrect": 0,
        "points_blank": 0,
        "points_multiple": 0,
        "negative_marking": 0,
        "rounding": "none",
    },
}, timeout=30)
resp.raise_for_status()
exam = resp.json()
print("created exam id:", exam["id"])

resp = httpx.post(f"{BASE}/exams/{exam['id']}/batches", timeout=30)
resp.raise_for_status()
batch = resp.json()
print("created batch id:", batch["id"])

sheet_path = "/home/murari/snap/viber/1/Downloads/omr/omr/Page0001.jpg"
with open(sheet_path, "rb") as f:
    resp = httpx.post(
        f"{BASE}/batches/{batch['id']}/items",
        files={"file": ("Page0001.jpg", f, "image/jpeg")},
        timeout=60,
    )
resp.raise_for_status()
item = resp.json()

print("\n--- result ---")
print("status:", item["status"])
print("error_code:", item.get("error_code"))
print("error_message:", item.get("error_message"))
print("score:", item.get("score"))
if item.get("raw_answers"):
    first_20 = {k: item["raw_answers"][k] for k in list(item["raw_answers"])[:20]}
    print("first 20 raw_answers:", first_20)
