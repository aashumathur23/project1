import boto3
from botocore.config import Config as BotoConfig
from flask import current_app


def _client():
    cfg = current_app.config
    kwargs = {
        "region_name": cfg["AWS_REGION"],
        "config": BotoConfig(signature_version="s3v4"),
    }
    # With an IAM role (EC2) leave the keys blank and boto3 finds the role itself.
    if cfg["AWS_ACCESS_KEY_ID"] and cfg["AWS_SECRET_ACCESS_KEY"]:
        kwargs["aws_access_key_id"] = cfg["AWS_ACCESS_KEY_ID"]
        kwargs["aws_secret_access_key"] = cfg["AWS_SECRET_ACCESS_KEY"]
    return boto3.client("s3", **kwargs)


def upload_fileobj(fileobj, key, content_type):
    _client().upload_fileobj(
        fileobj,
        current_app.config["S3_BUCKET"],
        key,
        ExtraArgs={"ContentType": content_type or "application/octet-stream"},
    )


def delete_object(key):
    _client().delete_object(Bucket=current_app.config["S3_BUCKET"], Key=key)


def presigned_url(key, filename, content_type, expires=300):
    """Short-lived link so the bucket can stay private."""
    return _client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": current_app.config["S3_BUCKET"],
            "Key": key,
            "ResponseContentType": content_type or "application/octet-stream",
            "ResponseContentDisposition": f'inline; filename="{filename}"',
        },
        ExpiresIn=expires,
    )
