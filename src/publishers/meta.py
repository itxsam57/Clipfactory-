from __future__ import annotations
import time, uuid, requests, boto3
from pathlib import Path
from ..config import env

def _r2_client():
    account = env("R2_ACCOUNT_ID", required=True)
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=env("R2_ACCESS_KEY_ID", required=True),
        aws_secret_access_key=env("R2_SECRET_ACCESS_KEY", required=True),
        region_name="auto",
    )

def stage_public(video_path: Path) -> tuple[str, str]:
    bucket = env("R2_BUCKET", required=True)
    base = env("R2_PUBLIC_BASE_URL", required=True).rstrip("/")
    key = f"clipfactory/{uuid.uuid4().hex}.mp4"
    _r2_client().upload_file(
        str(video_path), bucket, key, ExtraArgs={"ContentType": "video/mp4"}
    )
    return f"{base}/{key}", key

def cleanup(key: str) -> None:
    try:
        _r2_client().delete_object(
            Bucket=env("R2_BUCKET", required=True), Key=key
        )
    except Exception as exc:
        print("R2 cleanup warning:", exc)

def _graph(path: str, method="GET", data=None, params=None):
    version = env("META_GRAPH_VERSION", "v24.0")
    token = env("META_ACCESS_TOKEN", required=True)
    url = f"https://graph.facebook.com/{version}/{path.lstrip('/')}"
    if method == "POST":
        r = requests.post(
            url,
            data={**(data or {}), "access_token": token},
            params=params,
            timeout=60,
        )
    else:
        r = requests.get(
            url,
            params={**(params or {}), "access_token": token},
            timeout=60,
        )
    r.raise_for_status()
    return r.json()

def publish_instagram_reel(video_url: str, plan: dict) -> dict:
    ig = env("META_IG_USER_ID", required=True)
    caption = (
        plan["title"] + "\n\n" + plan["description"] + "\n\n"
        + " ".join(plan.get("hashtags", []))
    )[:2200]

    created = _graph(
        f"{ig}/media",
        method="POST",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
        },
    )
    creation_id = created["id"]

    for _ in range(30):
        status = _graph(creation_id, params={"fields": "status_code"})
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container failed: {status}")
        time.sleep(10)
    else:
        raise TimeoutError("Instagram media container did not finish in time")

    published = _graph(
        f"{ig}/media_publish",
        method="POST",
        data={"creation_id": creation_id},
    )
    return {"platform": "instagram", "id": published["id"]}

def publish_facebook_reel(video_url: str, plan: dict) -> dict:
    raise RuntimeError(
        "Facebook Reels is intentionally fail-closed until the current Page Reels "
        "upload flow is live-tested with your Meta app credentials."
    )
