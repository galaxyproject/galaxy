Galaxy-XSD
==========

A Galaxy XML tool wrapper __XML schema definition__ (__XSD__) 



# History

* Feb-2015 : Pierre Lindenbaum added doc, tests, Java-XML binding file (jxb) for java xml compiler (xjc)  ( https://docs.oracle.com/cd/E19575-01/819-3669/bnbal/index.html )
* 2013 : initial xsd by Jean-Fred

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

# See also:

* Galaxy https://usegalaxy.org/
* Galaxy Tool XML File https://wiki.galaxyproject.org/Admin/Tools/ToolConfigSyntax

