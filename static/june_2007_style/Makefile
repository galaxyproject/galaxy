OUT=blue
INI=$(OUT)_colors.ini

# The catch-all rule is magic, it reruns make in the OUT directory with a VPATH
all:
	@( cd blue; make -f ../Makefile VPATH=.. css )

ALL_CSS=base panel_layout masthead library history tool_menu iphone autocomplete_tagging trackster

css: $(foreach N,$(ALL_CSS),$N.css)

# Convert variables from ini to less syntax
variables.less : $(INI)
	../variables_to_less.py < $< > $@

# Convert using less
%.css : %.less
	lessc -x $< $@

# Old style using process_css still works so we can move gradually
%.css : %.css.tmpl
	../process_css.py ../$(INI) ..:../shared_images:../../images . < $< > $@

# For building sprite images
%.less : %.less.tmpl
	../process_css.py ../$(INI) ..:../shared_images:../../images . < $< > $@

# Some dependencies
base.css: variables.less galaxy_bootstrap.less iconic_stroke.less base_sprites.less

