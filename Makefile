udevdir := $(shell pkg-config --define-variable=prefix=$(prefix) --variable=udevdir udev 2>/dev/null \
             || echo $(libdir)/udev/)

install:
	install -D -m755 ds-inhibit.py "$(DESTDIR)/usr/bin/ds-inhibit"
	install -D -m755 udev-register.sh "$(DESTDIR)/usr/bin/ds-inhibit-register"
	install -D -m644 udev.rules "$(DESTDIR)$(udevdir)/90-ds-inhibit.rules"
