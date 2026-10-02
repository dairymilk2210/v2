from io import BytesIO
from botocore.exceptions import ClientError

from lib import storage


def test_private_s3_upload_and_download(monkeypatch):
    objects = {}

    class S3:
        def upload_fileobj(self, stream, bucket, key, ExtraArgs):
            assert bucket == "private-test-bucket"
            assert ExtraArgs["ServerSideEncryption"] == "AES256"
            assert "ACL" not in ExtraArgs
            objects[key] = (stream.read(), ExtraArgs["ContentType"])

        def get_object(self, Bucket, Key):
            data, mime = objects[Key]
            return {"Body": BytesIO(data), "ContentType": mime}

    monkeypatch.setattr(storage, "S3_BUCKET", "private-test-bucket")
    monkeypatch.setattr(storage.boto3, "client", lambda *args, **kwargs: S3())
    result = storage.put_object("poonji-finance/careers/file.pdf", b"%PDF-test", "application/pdf")
    assert result["path"] == "poonji-finance/careers/file.pdf"
    assert storage.get_object(result["path"]) == (b"%PDF-test", "application/pdf")


def test_legacy_disk_object_can_be_read_during_migration(monkeypatch, tmp_path):
    key = "poonji-finance/careers/old.pdf"
    path = tmp_path / key
    path.parent.mkdir(parents=True)
    path.write_bytes(b"%PDF-old")

    class MissingS3:
        def get_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")

    monkeypatch.setattr(storage, "S3_BUCKET", "private-test-bucket")
    monkeypatch.setattr(storage, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(storage.boto3, "client", lambda *args, **kwargs: MissingS3())
    assert storage.get_object(key) == (b"%PDF-old", "application/pdf")
