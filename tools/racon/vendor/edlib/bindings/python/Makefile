default: build

############### FILES #################
FILES=edlib pyedlib.bycython.cpp setup.py MANIFEST.in README.rst

edlib: ../../edlib
	cp -R ../../edlib .

pyedlib.bycython.cpp: edlib.pyx cedlib.pxd
	cython --cplus edlib.pyx -o edlib.bycython.cpp
#######################################

############## COMMANDS ###############
build: ${FILES}
	python setup.py build_ext -i

sdist: ${FILES}
	python setup.py sdist

publish: clean sdist
	twine upload dist/*

clean:
	rm -rf edlib dist edlib.egg-info build
	rm -f edlib.c *.bycython.* edlib.*.so
#######################################
