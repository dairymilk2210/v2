"""Copy legacy Render disk files to S3 under the same keys; dry-run by default.

Run from backend/ with FILE_STORAGE_DIR and S3_BUCKET configured:
    python migrate_storage.py
    python migrate_storage.py --apply
Mongo paths do not change. Verify downloads before detaching the disk.
"""

import argparse
import mimetypes

from lib.storage import S3_BUCKET, STORAGE_DIR, put_object


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="upload files; without this, only count them")
    args = parser.parse_args()
    if not S3_BUCKET:
        parser.error("S3_BUCKET must be configured")
    files = [path for path in STORAGE_DIR.rglob("*") if path.is_file() and not path.is_symlink()]
    print(f"Found {len(files)} legacy files under {STORAGE_DIR}")
    if not args.apply:
        print("Dry run only. Pass --apply to upload them.")
        return
    for path in files:
        key = path.relative_to(STORAGE_DIR).as_posix()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        put_object(key, path.read_bytes(), content_type)
    print(f"Uploaded {len(files)} files to {S3_BUCKET}; verify downloads before removing the disk.")


if __name__ == "__main__":
    main()
