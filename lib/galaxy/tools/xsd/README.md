Galaxy-XSD
==========
[![Build Status](https://travis-ci.org/JeanFred/Galaxy-XSD.svg)](http://travis-ci.org/JeanFred/Galaxy-XSD)
[![License](http://img.shields.io/badge/license-MIT-orange.svg?style=flat)](http://opensource.org/licenses/MIT)

A Galaxy XML tool wrapper __XML schema definition__ (__XSD__) 



# History

* Feb-2015 : Pierre Lindenbaum added doc, tests, Java-XML binding file (jxb) for java xml compiler (xjc)  ( https://docs.oracle.com/cd/E19575-01/819-3669/bnbal/index.html )
* 2013 : extraction to standalone and improvements by Jean-Fred
* 2011 : Initial work by John Chilton

# Validating a `tool.xml`

```bash
$ xmllint --noout --schema galaxy.xsd tool.xml 
```

# Creating java code

```bash
$  ${JAVA_HOME}/bin/xjc -b galaxy.jxb galaxy.xsd 
```


# Authors

* Jean-Frédéric @JeanFred
* Pierre Lindenbaum @yokofakun
* John Chilton @jmchilton


# Licence

This code is free software released under the terms of the MIT license.


# See also:

* Galaxy https://usegalaxy.org/
* Galaxy Tool XML File https://wiki.galaxyproject.org/Admin/Tools/ToolConfigSyntax

