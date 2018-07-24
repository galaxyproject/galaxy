#!/bin/sh

if command -v ack-grep >/dev/null; then
    ACK=ack-grep
else
    ACK=ack
fi

export ACK_OPTIONS=" --type python \
--ignore-dir=.git \
--ignore-dir=.tox \
--ignore-dir=.venv \
--ignore-dir=.venv3 \
--ignore-dir=client/node_modules \
--ignore-dir=database \
--ignore-dir=doc/build \
--ignore-dir=eggs \
--ignore-dir=static/maps \
--ignore-dir=static/scripts"

PYTHON2_ONLY_MODULES="__builtin__ _winreg BaseHTTPServer CGIHTTPServer \
ConfigParser Cookie cookielib copy_reg cPickle cStringIO Dialog dummy_thread \
FileDialog gdbm htmlentitydefs HTMLParser httplib Queue robotparser \
ScrolledText SimpleDialog SimpleHTTPServer SimpleXMLRPCServer SocketServer \
StringIO thread Tix tkColorChooser tkCommonDialog Tkconstants Tkdnd tkFont \
Tkinter tkFileDialog tkMessageBox tkSimpleDialog ttk urllib urllib2 urlparse \
xmlrpclib"

ret=0
for mod in $PYTHON2_ONLY_MODULES; do
    $ACK "^import $mod(\n|\.)|^from $mod import "
    if [ $? -eq 0 ]; then ret=1; fi
done

exit $ret
