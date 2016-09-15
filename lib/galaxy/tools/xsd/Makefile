SHELL=/bin/bash
.PHONY: all clean tests

all: tests

tests: galaxy.xsd galaxy.jxb  generated/ObjectFactory.java
	sed "s%^%https://bitbucket.org/galaxy/galaxy-central/raw/c3eefbdaaa1ab242a1c81b65482ef2fbe943a390/%" test.urls |\
	while read L; do echo "#$${L}" && curl -ksL "$${L}" | xmllint --noout --schema $< - ; done


generated/ObjectFactory.java : galaxy.jxb galaxy.xsd
	$(if $(realpath ${JAVA_HOME}/bin/xjc),xjc -b $^)

clean:
	rm -rf generated
