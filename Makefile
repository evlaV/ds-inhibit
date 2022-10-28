systemdunitsdir := $(shell pkg-config --define-variable=prefix=$(prefix) --variable=systemdsystemunitdir systemd 2>/dev/null \
                     || echo $(libdir)/systemd/system/)
udevdir := $(shell pkg-config --define-variable=prefix=$(prefix) --variable=udevdir udev 2>/dev/null \
                     || echo $(libdir)/udev/)

install:
	install -D -m755 ds-inhibit.py "$(DESTDIR)/usr/bin/ds-inhibit"
	install -D -m755 udev-register.sh "$(DESTDIR)/usr/bin/ds-inhibit-register"
	install -D -m644 udev.rules "$(DESTDIR)$(udevdir)/rules.d/90-ds-inhibit.rules"
	install -D -m644 systemd.service "$(DESTDIR)$(systemdunitsdir)/ds-inhibit.service"
