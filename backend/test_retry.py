import httpx

BASE = "http://127.0.0.1:8000/api/v1"

answer_key = [{"question": i, "correct_option": "A"} for i in range(1, 201)]
resp = httpx.post(f"{BASE}/exams", json={
    "title": "retry test", "template_version": "ambition-guru-v1",
    "answer_key": answer_key,
    "scoring_policy": {"points_correct": 1, "points_incorrect": 0, "points_blank": 0,
                        "points_multiple": 0, "negative_marking": 0, "rounding": "none"},
}, timeout=30)
exam = resp.json()
resp = httpx.post(f"{BASE}/exams/{exam['id']}/batches", timeout=30)
batch = resp.json()
bid = batch["id"]
print("batch:", bid)

# upload garbage bytes - should fail
resp = httpx.post(f"{BASE}/batches/{bid}/items",
    files={"file": ("bad.jpg", b"not a real image", "image/jpeg")}, timeout=30)
item = resp.json()
print("after bad upload:", item["status"], item.get("error_code"))

resp = httpx.get(f"{BASE}/batches/{bid}", timeout=10)
print("batch aggregate after failure:", resp.json())

# now retry with a real sheet
item_id = item["id"]
with open("/home/murari/snap/viber/1/Downloads/omr/omr/Page0001.jpg", "rb") as f:
    resp = httpx.post(f"{BASE}/batches/{bid}/items/{item_id}/retry",
        files={"file": ("Page0001.jpg", f, "image/jpeg")}, timeout=30)
print("\nafter retry submitted:", resp.json()["status"])

import time
for _ in range(20):
    time.sleep(0.2)
    resp = httpx.get(f"{BASE}/batches/{bid}/items/{item_id}", timeout=10)
    it = resp.json()
    if it["status"] in ("completed", "needs_review", "failed"):
        break
print("final item status:", it["status"], "attempt:", it.get("attempt"))

resp = httpx.get(f"{BASE}/batches/{bid}", timeout=10)
print("final batch aggregate:", resp.json())
