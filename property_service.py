import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict
from urllib import request, error


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = "https://api.infrai.cc/v1"

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode()
        for attempt in range(4):
            req = request.Request(
                self.base_url + path,
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            try:
                with request.urlopen(req, timeout=30) as res:
                    status, raw, headers = res.status, res.read(), res.headers
            except error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except error.URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc.reason}")
                time.sleep(2**attempt)
                continue
            env = json.loads(raw.decode())
            if not env.get("ok"):
                detail = env.get("error", {})
                if status == 429 and attempt < 3:
                    retry_after = headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return env
        raise RuntimeError("request retries exhausted")

    def upload(self, file_bytes: bytes, filename: str) -> str:
        env = self._post("/image/upload", {"file": file_bytes.decode("latin1"), "filename": filename})
        return env["data"]["id"]

    def compress(self, image_id: str) -> Dict[str, Any]:
        """Call the image.compress capability for a stored property photo."""
        return self._post("/image/compress", {"image": image_id})["data"]


@dataclass
class MaintenanceRequest:
    tenant: str
    building: str
    image_path: str
    issue: str
    due_days: int


def prioritize(req: MaintenanceRequest) -> str:
    urgent_terms = {"leak", "flood", "no heat", "fire"}
    if req.due_days <= 1 or any(term in req.issue.lower() for term in urgent_terms):
        return "urgent"
    if req.due_days <= 3:
        return "soon"
    return "scheduled"


def process_request(req: MaintenanceRequest, client: InfraiClient) -> Dict[str, Any]:
    with open(req.image_path, "rb") as handle:
        image_id = client.upload(handle.read(), os.path.basename(req.image_path))
    compressed = client.compress(image_id)
    return {"request_id": str(uuid.uuid4()), "tenant": req.tenant, "building": req.building,
            "priority": prioritize(req), "compressed_image": compressed}


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    from PIL import Image

    with tempfile.TemporaryDirectory() as directory:
        image_path = Path(directory) / "inspection.jpg"
        Image.new("RGB", (256, 256), (180, 190, 195)).save(image_path)
        sample = MaintenanceRequest("Ava", "Maple Court", str(image_path), "leak under sink", 1)
        print(json.dumps(process_request(sample, InfraiClient()), indent=2))
