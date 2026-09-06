import time
import httpx
import os

BASE = "http://127.0.0.1:8000/api/v1"
SHEET_DIR = "/home/murari/snap/viber/1/Downloads/omr/omr"

answer_key = [{"question": i, "correct_option": "A"} for i in range(1, 201)]
resp = httpx.post(f"{BASE}/exams", json={
    "title": "Day 4 batch test",
    "template_version": "ambition-guru-v1",
    "answer_key": answer_key,
    "scoring_policy": {"points_correct": 1, "points_incorrect": 0, "points_blank": 0,
                        "points_multiple": 0, "negative_marking": 0, "rounding": "none"},
}, timeout=30)
exam = resp.json()
resp = httpx.post(f"{BASE}/exams/{exam['id']}/batches", timeout=30)
batch = resp.json()
print("exam:", exam["id"], "batch:", batch["id"])

pages = sorted(f for f in os.listdir(SHEET_DIR) if f.endswith(".jpg"))[:5]
print("uploading:", pages)

t0 = time.time()
item_ids = []
for p in pages:
    with open(os.path.join(SHEET_DIR, p), "rb") as f:
        resp = httpx.post(
            f"{BASE}/batches/{batch['id']}/items",
            files={"file": (p, f, "image/jpeg")}, timeout=30,
        )
    item_ids.append(resp.json()["id"])
t1 = time.time()
print(f"all 5 uploads returned in {t1-t0:.2f}s total\n")

for i in range(40):
    resp = httpx.get(f"{BASE}/batches/{batch['id']}/items", timeout=10)
    items = resp.json()
    line = "  ".join(f"#{it['id']}:{it['status']}/{it.get('stage')}/{it.get('progress')}%" for it in items)
    print(f"t+{i*0.2:.1f}s  {line}")
    if all(it["status"] in ("completed", "needs_review", "failed") for it in items):
        break
    time.sleep(0.2)

resp = httpx.get(f"{BASE}/batches/{batch['id']}", timeout=10)
print("\nfinal batch aggregate:", resp.json())
