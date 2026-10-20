#!/usr/bin/env bash
# Build the verified onboarding archive attached to a GitHub release.
set -euo pipefail

usage() {
    echo "usage: $0 VERSION [OUTPUT_DIR]" >&2
    exit 2
}

version="${1:-}"
output="${2:-dist}"
if [ -z "$version" ]; then
    usage
fi
version="${version#v}"
if ! printf '%s' "$version" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$'; then
    echo "Invalid version: $version" >&2
    exit 2
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
stage="$output/ai-guardian-lab-$version"
archive="$output/ai-guardian-lab-$version.tar.gz"
mkdir -p "$output"
rm -rf "$stage" "$archive" "$archive.sha256"
mkdir -p "$stage/state/audit" "$stage/state/learned"

cp "$root/docker-compose.release.yml" "$stage/docker-compose.yml"
sed -i "s/IMAGE_TAG:-1.4.0/IMAGE_TAG:-$version/g" "$stage/docker-compose.yml"
cp "$root/guardian-lab" "$stage/guardian-lab"
chmod +x "$stage/guardian-lab"
cp -R "$root/tools" "$stage/tools"
cp -R "$root/guardian/config" "$stage/guardian-config"
mkdir -p "$stage/guardian"
mv "$stage/guardian-config" "$stage/guardian/config"
cp -R "$root/database" "$stage/database"
mkdir -p "$stage/scripts"
cp "$root/scripts/verify_logs.py" "$stage/scripts/verify_logs.py"
cp -R "$root/docs" "$stage/docs"
cp "$root/README.md" "$root/LICENSE" "$root/.env.example" "$stage/"

# Runtime caches and bytecode are not release content.
find "$stage" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$stage" -type f -name '*.pyc' -delete

(
    cd "$stage"
    find . -type f ! -name SHA256SUMS -print0 \
        | sort -z \
        | xargs -0 sha256sum > SHA256SUMS
)

epoch="${SOURCE_DATE_EPOCH:-}"
if [ -z "$epoch" ] && git -C "$root" rev-parse --git-dir >/dev/null 2>&1; then
    epoch="$(git -C "$root" log -1 --format=%ct)"
fi
epoch="${epoch:-$(date +%s)}"

tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner \
    -czf "$archive" -C "$output" "ai-guardian-lab-$version"
(
    cd "$output"
    sha256sum "ai-guardian-lab-$version.tar.gz" > "ai-guardian-lab-$version.tar.gz.sha256"
)

echo "Bundle: $archive"
echo "Checksum: $archive.sha256"
