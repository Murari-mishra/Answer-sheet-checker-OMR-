"""
Tests the Day 4 behavior: upload should return almost instantly (202),
then polling the item should show it moving through queued -> processing
(with stage/progress) -> completed/needs_review.
"""
import time
import httpx

BASE = "http://127.0.0.1:8000/api/v1"

answer_key = [{"question": i, "correct_option": "A"} for i in range(1, 201)]
resp = httpx.post(f"{BASE}/exams", json={
    "title": "Day 4 async test",
    "template_version": "ambition-guru-v1",
    "answer_key": answer_key,
    "scoring_policy": {"points_correct": 1, "points_incorrect": 0, "points_blank": 0,
                        "points_multiple": 0, "negative_marking": 0, "rounding": "none"},
}, timeout=30)
exam = resp.json()

resp = httpx.post(f"{BASE}/exams/{exam['id']}/batches", timeout=30)
batch = resp.json()
print("exam:", exam["id"], "batch:", batch["id"])

sheet_path = "/home/murari/snap/viber/1/Downloads/omr/omr/Page0001.jpg"

t0 = time.time()
with open(sheet_path, "rb") as f:
    resp = httpx.post(
        f"{BASE}/batches/{batch['id']}/items",
        files={"file": ("Page0001.jpg", f, "image/jpeg")},
        timeout=30,
    )
t1 = time.time()
print(f"\nupload responded in {t1-t0:.2f}s with HTTP {resp.status_code}")
item = resp.json()
print("initial item status:", item["status"], "stage:", item.get("stage"), "progress:", item.get("progress"))

item_id = item["id"]
print("\npolling...")
for i in range(30):
    time.sleep(0.3)
    resp = httpx.get(f"{BASE}/batches/{batch['id']}/items/{item_id}", timeout=10)
    it = resp.json()
    print(f"  t+{i*0.3:.1f}s: status={it['status']} stage={it.get('stage')} progress={it.get('progress')}")
    if it["status"] in ("completed", "needs_review", "failed"):
        break

print("\nfinal status:", it["status"], "score:", it.get("score"))
