#!/usr/bin/env bash
# UPLOAD the asset library to the Cloudflare R2 cache (WS9 task 3). OWNER-APPROVED RUNS ONLY.
# Uploads library/scans/<id>/... -> s3://$R2_BUCKET/library/scans/<id>/... and, if given, out/built/ -> built/.
# Only files that are missing or changed are sent (aws s3 sync), so running it again is cheap.
#
# Needs (in .env, never printed, never committed):
#   R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET   (an R2 API token scoped to this ONE bucket)
# and the AWS CLI (free):  winget install Amazon.AWSCLI   (R2 speaks the same S3 protocol)
#
# Usage:  bash cloud/r2_push.sh [--built out/built] [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."

# Budget check first: refuse to upload if the library would pass its 6 GB share of the free 10 GB.
python -m tc cache index || { echo "library over its R2 budget: not uploading"; exit 1; }

set -a; . ./.env; set +a                     # load keys into the environment (not echoed)
: "${R2_ACCOUNT_ID:?missing in .env}" "${R2_ACCESS_KEY_ID:?missing in .env}" "${R2_SECRET_ACCESS_KEY:?missing in .env}" "${R2_BUCKET:?missing in .env}"
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" AWS_DEFAULT_REGION=auto
EP="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

DRY=""; BUILT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY="--dryrun" ;;
    --built) BUILT="$2"; shift ;;
  esac; shift
done

# --size-only: Poly Haven files never change in place, so size is enough (and faster than checksums).
aws s3 sync library/scans "s3://$R2_BUCKET/library/scans" --endpoint-url "$EP" --size-only $DRY --exclude "*.part"
aws s3 cp library/scans_index.json "s3://$R2_BUCKET/library/scans_index.json" --endpoint-url "$EP" $DRY
if [ -n "$BUILT" ]; then
  aws s3 sync "$BUILT" "s3://$R2_BUCKET/built" --endpoint-url "$EP" --size-only $DRY
fi
echo "R2 upload finished${DRY:+ (dry run: nothing sent)}"
