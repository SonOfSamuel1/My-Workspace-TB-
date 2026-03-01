#!/usr/bin/env python3
"""
Sync JT- Obsidian notes to S3.

Run this once (and again whenever notes are updated) to upload
all JT-*.md files from your local vault to the S3 bucket.

Usage:
  python scripts/sync_to_s3.py \
    --vault "/Users/terrancebrandon/Valuts (sync)/Terrance (Primary Vault)/Permanent Notes" \
    --bucket jt-teachings-notes

Options:
  --vault     Path to Obsidian vault folder containing JT-*.md files
  --bucket    S3 bucket name
  --region    AWS region (default: us-east-1)
  --dry-run   Print what would be uploaded without actually uploading
  --prefix    File prefix to match (default: JT-)
"""

import argparse
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def sync_vault_to_s3(
    vault_path: str,
    bucket: str,
    region: str = "us-east-1",
    prefix: str = "JT-",
    dry_run: bool = False,
) -> int:
    """
    Upload all matching .md files from vault to S3.

    Returns:
        Number of files uploaded (or that would be uploaded in dry-run)
    """
    vault = Path(vault_path)
    if not vault.exists():
        print(f"ERROR: Vault path does not exist: {vault}")
        sys.exit(1)

    # Find all matching files
    md_files = sorted([f for f in vault.glob(f"{prefix}*.md")])

    if not md_files:
        print(f"No files matching '{prefix}*.md' found in: {vault}")
        sys.exit(1)

    print(f"Found {len(md_files)} files matching '{prefix}*.md'")
    print(f"Target: s3://{bucket}/")
    if dry_run:
        print("DRY RUN — no files will be uploaded\n")
    else:
        print()

    s3 = boto3.client("s3", region_name=region)

    # Ensure bucket exists
    if not dry_run:
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("404", "NoSuchBucket"):
                print(f"Bucket '{bucket}' does not exist. Creating it...")
                try:
                    if region == "us-east-1":
                        s3.create_bucket(Bucket=bucket)
                    else:
                        s3.create_bucket(
                            Bucket=bucket,
                            CreateBucketConfiguration={"LocationConstraint": region},
                        )
                    print(f"Bucket '{bucket}' created.")
                except ClientError as create_err:
                    print(f"ERROR: Could not create bucket: {create_err}")
                    sys.exit(1)
            else:
                print(f"ERROR accessing bucket: {e}")
                sys.exit(1)

    uploaded = 0
    skipped = 0
    errors = 0

    for md_file in md_files:
        s3_key = md_file.name  # Just the filename, no subdirectory

        if dry_run:
            print(f"  [DRY RUN] Would upload: {md_file.name}")
            uploaded += 1
            continue

        try:
            # Check if file already exists with same size (simple change detection)
            try:
                head = s3.head_object(Bucket=bucket, Key=s3_key)
                remote_size = head["ContentLength"]
                local_size = md_file.stat().st_size
                if remote_size == local_size:
                    skipped += 1
                    continue
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise
                # File doesn't exist yet — upload it

            with open(md_file, "rb") as f:
                s3.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType="text/markdown; charset=utf-8",
                )
            print(f"  Uploaded: {md_file.name}")
            uploaded += 1

        except Exception as e:
            print(f"  ERROR uploading {md_file.name}: {e}")
            errors += 1

    print()
    if dry_run:
        print(f"DRY RUN complete: {uploaded} files would be uploaded")
    else:
        print(
            f"Sync complete: {uploaded} uploaded, {skipped} unchanged, {errors} errors"
        )

    if errors:
        sys.exit(1)

    return uploaded


def main():
    parser = argparse.ArgumentParser(description="Sync JT- Obsidian notes to S3")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault folder")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument(
        "--region", default="us-east-1", help="AWS region (default: us-east-1)"
    )
    parser.add_argument(
        "--prefix", default="JT-", help="File prefix to match (default: JT-)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without uploading"
    )
    args = parser.parse_args()

    sync_vault_to_s3(
        vault_path=args.vault,
        bucket=args.bucket,
        region=args.region,
        prefix=args.prefix,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
