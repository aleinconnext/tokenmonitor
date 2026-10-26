VERSION ?= $(shell awk '/^Version:/{print $$2}' packaging/control)
PYTHON  ?= python3
HOME    ?= $(shell echo ~)

.PHONY: run user-install autostart uninstall deb clean

run:
	GDK_BACKEND=x11 $(PYTHON) src/tokenmon.py

user-install:
	install -Dm644 src/tokenmon.py $(HOME)/.local/share/tokenmonitor/tokenmon.py
	printf '#!/bin/sh\nexport GDK_BACKEND=x11\nexec $(PYTHON) "$$HOME/.local/share/tokenmonitor/tokenmon.py" "$$@"\n' > $(HOME)/.local/bin/tokenmonitor
	chmod 755 $(HOME)/.local/bin/tokenmonitor
	install -Dm644 packaging/tokenmonitor.desktop $(HOME)/.local/share/applications/tokenmonitor.desktop
	sed -i 's|^Exec=.*|Exec=$(HOME)/.local/bin/tokenmonitor|' $(HOME)/.local/share/applications/tokenmonitor.desktop
	-@command -v update-desktop-database >/dev/null && update-desktop-database $(HOME)/.local/share/applications

autostart:
	mkdir -p $(HOME)/.config/autostart
	printf '[Desktop Entry]\nType=Application\nName=Token Monitor\nComment=Usage monitor for Claude Code, Cursor and Codex\nExec=sh -c "sleep 4; exec $(HOME)/.local/bin/tokenmonitor"\nIcon=tokenmonitor\nTerminal=false\nX-GNOME-Autostart-enabled=true\n' > $(HOME)/.config/autostart/tokenmonitor.desktop

uninstall:
	rm -f $(HOME)/.local/bin/tokenmonitor
	rm -f $(HOME)/.local/share/applications/tokenmonitor.desktop
	rm -f $(HOME)/.config/autostart/tokenmonitor.desktop
	rm -rf $(HOME)/.local/share/tokenmonitor

deb:
	./scripts/build-deb.sh $(VERSION)

clean:
	rm -rf build dist
