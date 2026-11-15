import io
import os
import urllib.parse

import boto3
from PIL import Image

s3 = boto3.client("s3")

DEST_BUCKET = os.environ["DEST_BUCKET"]
THUMBNAIL_SIZE = (128, 128)


def get_bucket_and_key(event):
    """Works for both S3 upload events and direct input from Step Functions."""
    if "Records" in event:
        record = event["Records"][0]["s3"]
        bucket = record["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["object"]["key"])
    else:
        bucket = event["bucket"]
        key = event["key"]
    return bucket, key


def lambda_handler(event, context):
    try:
        bucket, key = get_bucket_and_key(event)

        obj = s3.get_object(Bucket=bucket, Key=key)
        image = Image.open(io.BytesIO(obj["Body"].read()))
        image_format = image.format or "JPEG"

        image.thumbnail(THUMBNAIL_SIZE)
        if image_format == "JPEG" and image.mode != "RGB":
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format=image_format)
        buffer.seek(0)

        out_key = f"thumb-{key}"
        s3.put_object(
            Bucket=DEST_BUCKET,
            Key=out_key,
            Body=buffer,
            ContentType=obj.get("ContentType", "image/jpeg"),
        )
        print(f"Resized {bucket}/{key} -> {DEST_BUCKET}/{out_key}")
        return {"success": True, "bucket": DEST_BUCKET, "key": out_key}

    except Exception as e:
        print(f"Resize failed: {e}")
        return {"success": False, "error": str(e)}
