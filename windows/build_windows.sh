#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------
# 1️⃣  Atualiza a branch atual (main) e pega a última tag
# -------------------------------------------------
git fetch --tags
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Última tag: $LAST_TAG"

# -------------------------------------------------
# 2️⃣  Incrementa PATCH (vMAJOR.MINOR.PATCH)
# -------------------------------------------------
# Remove o 'v' e separa os números
MAJOR_MINOR_PATCH="${LAST_TAG#v}"
IFS='.' read -r MAJOR MINOR PATCH <<<"$MAJOR_MINOR_PATCH"
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
echo "Nova versão: $NEW_VERSION"

# -------------------------------------------------
# 3️⃣  Atualiza o arquivo CHANGELOG.md (primeira linha)
# -------------------------------------------------
# Insere a nova versão no topo do CHANGELOG
if [ -f "CHANGELOG.md" ]; then
  # Insere a nova seção antes da primeira linha existente
  NEW_ENTRY="## $NEW_VERSION - $(date +%Y-%m-%d)
---
### Added
- Initial Windows installer support (installer.exe).
### Changed
-
### Fixed
-"
  # Prepend (não remove as seções antigas, apenas adiciona no topo)
  TEMP=$(cat CHANGELOG.md)
  echo "$NEW_ENTRY" > CHANGELOG.md
  echo "$TEMP" >> CHANGELOG.md
fi

# -------------------------------------------------
# 4️⃣  Commit da atualização do CHANGELOG e da tag
# -------------------------------------------------
git add CHANGELOG.md
git commit -m "chore: bump version to $NEW_VERSION"
git tag "v$NEW_VERSION"

# -------------------------------------------------
# 5️⃣  Baixa o runtime GTK para Windows (64‑bit)
# -------------------------------------------------
mkdir -p windows/gtk
GTK_URL="https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment/releases/download/gtk-4.14.0/gtk-4.14.0-win64.zip"
echo "Baixando GTK runtime de $GTK_URL ..."
curl -L -o windows/gtk.zip "$GTK_URL"
mkdir -p windows/gtk-tmp
tar -xf windows/gtk.zip -C windows/gtk-tmp --strip-components=1
mv windows/gtk-tmp/* windows/gtk/
rm -rf windows/gtk-tmp windows/gtk.zip
echo "GTK runtime extraído em windows/gtk/"

# -------------------------------------------------
# 6️⃣  Instala dependências Python (PyInstaller + PyGObject wheel)
# -------------------------------------------------
python -m pip install --upgrade pip
pip install pyinstaller==6.10.0
# Instala a wheel do PyGObject para Windows (versão compatível com Python 3.12 x64)
PIP_URL="https://github.com/tschoonj/pygobject-win-build/releases/download/pygobject-3.48.2/pygobject-3.48.2-cp312-cp312-win_amd64.whl"
echo "Instalando PyGObject wheel..."
pip install "$PIP_URL"

# -------------------------------------------------
# 7️⃣  Cria o executável com PyInstaller
# -------------------------------------------------
cd windows
echo "Executando PyInstaller..."
pyinstaller tokenmonitor.spec
cd ..

# -------------------------------------------------
# 8️⃣  Compila o instalador .exe com Inno Setup
# -------------------------------------------------
# Espera-se que o Inno Setup esteja instalado em C:\Program Files (x86)\Inno Setup 6\
ISCC="/c/Program Files (x86)/Inno Setup 6/ISCC.exe"
if [ ! -x "$ISCC" ]; then
  echo "⚠️  Inno Setup não encontrado em $ISCC – instalando via Chocolatey (apenas Windows)."
  # No Linux não conseguimos instalar Chocolatey; avise o usuário.
  echo "Por favor, instale o Inno Setup manualmente e execute o script novamente."
  exit 1
fi
echo "Compilando instalador com Inno Setup..."
"$ISCC" windows/tokenmonitor.iss

# -------------------------------------------------
# 9️⃣  Cria a Release no GitHub (usando gh CLI)
# -------------------------------------------------
# O script presume que o usuário já tenha feito login:
#   gh auth login
#   gh auth refresh -h github.com -s repo,write:repo_hook
TAG_NAME="${NEW_VERSION#v}"
RELEASE_NOTES="Release automática gerada pelo script de build Windows.\n\n**O que há de novo:**\n- Instalador .exe (um‑clique).\n- Integração completa com GTK 4.\n- Suporte a Docker/FreeLLMAPI (quando disponível).\n- Persistência de estado em %APPDATA%\\tokenmonitor."

echo "Criando release GitHub v$TAG_NAME ..."
gh release create "v$TAG_NAME" \
    "windows/TokenMonitor-${TAG_NAME}-win.exe" \
    --title "TokenMonitor $TAG_NAME – Windows Installer" \
    --notes "$RELEASE_NOTES"

echo "✅  Release v$TAG_NAME publicada com sucesso!"
echo "Artefato: windows/TokenMonitor-${TAG_NAME}-win.exe"