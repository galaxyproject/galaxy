static: static/welcome.html
static: static/help.html
static: static/galaxyIndex.html

%.html : %.rst
	./modules/rst2html.py --stylesheet="/static/help.css" --initial-header-level=2 < $< > $@

convert_images:
	for f in src/images/*.psd; do \
		convert $$f static/images/`basename $${f%%psd}png`; \
	done
