#!/usr/bin/env bash
# Build an architecture-independent .deb for tokenmonitor.
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="${1:-$(awk '/^Version:/{print $2}' packaging/control)}"
ROOT="build/tokenmonitor"

rm -rf build dist

install -d \
  "$ROOT/DEBIAN" \
  "$ROOT/usr/bin" \
  "$ROOT/usr/lib/tokenmonitor" \
  "$ROOT/usr/share/applications" \
  "$ROOT/usr/share/icons/hicolor/scalable/apps"

install -m644 src/tokenmon.py                    "$ROOT/usr/lib/tokenmonitor/tokenmon.py"
install -m755 packaging/tokenmonitor             "$ROOT/usr/bin/tokenmonitor"
install -m644 packaging/tokenmonitor.desktop     "$ROOT/usr/share/applications/tokenmonitor.desktop"
install -m644 packaging/tokenmonitor.svg         "$ROOT/usr/share/icons/hicolor/scalable/apps/tokenmonitor.svg"

sed "s/^Version:.*/Version: $VERSION/" packaging/control > "$ROOT/DEBIAN/control"
chmod 644 "$ROOT/DEBIAN/control"

mkdir -p dist
dpkg-deb --build --root-owner-group "$ROOT" "dist/tokenmonitor_${VERSION}_all.deb"

echo "built dist/tokenmonitor_${VERSION}_all.deb"
