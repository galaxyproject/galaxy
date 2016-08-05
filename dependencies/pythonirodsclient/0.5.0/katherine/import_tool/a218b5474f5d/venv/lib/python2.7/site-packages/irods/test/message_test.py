#!/usr/bin/env python
import os
import sys
import unittest

# this does not get called when imported from  runner.py
if __name__ == '__main__':
    sys.path.insert(0, os.path.abspath('../..'))

from xml.etree import ElementTree as ET
# from base64 import b64encode, b64decode
from irods.message import (StartupPack, AuthResponse, IntegerIntegerMap,
                           IntegerStringMap, StringStringMap, GenQueryRequest,
                           GenQueryResponseColumn, GenQueryResponse)


class TestMessages(unittest.TestCase):

    def test_startup_pack(self):
        sup = StartupPack(('rods', 'tempZone'), ('rods', 'tempZone'))
        sup.irodsProt = 2
        sup.reconnFlag = 3
        sup.proxyUser = "rods"
        sup.proxyRcatZone = "tempZone"
        sup.clientUser = "rods"
        sup.clientRcatZone = "yoyoyo"
        sup.relVersion = "irods3.2"
        sup.apiVersion = "d"
        sup.option = "hellO"
        xml_str = sup.pack()
        expected = "<StartupPack_PI>\
<irodsProt>2</irodsProt>\
<reconnFlag>3</reconnFlag>\
<connectCnt>0</connectCnt>\
<proxyUser>rods</proxyUser>\
<proxyRcatZone>tempZone</proxyRcatZone>\
<clientUser>rods</clientUser>\
<clientRcatZone>yoyoyo</clientRcatZone>\
<relVersion>irods3.2</relVersion>\
<apiVersion>d</apiVersion>\
<option>hellO</option>\
</StartupPack_PI>"
        self.assertEqual(xml_str, expected)

        sup2 = StartupPack(('rods', 'tempZone'), ('rods', 'tempZone'))
        sup2.unpack(ET.fromstring(expected))
        self.assertEqual(sup2.irodsProt, 2)
        self.assertEqual(sup2.reconnFlag, 3)
        self.assertEqual(sup2.proxyUser, "rods")
        self.assertEqual(sup2.proxyRcatZone, "tempZone")
        self.assertEqual(sup2.clientUser, "rods")
        self.assertEqual(sup2.clientRcatZone, "yoyoyo")
        self.assertEqual(sup2.relVersion, "irods3.2")
        self.assertEqual(sup2.apiVersion, "d")
        self.assertEqual(sup2.option, "hellO")

    def test_auth_response(self):
        ar = AuthResponse()
        ar.response = "hello"
        ar.username = "rods"
        expected = "<authResponseInp_PI>\
<response>aGVsbG8=</response>\
<username>rods</username>\
</authResponseInp_PI>"
        self.assertEqual(ar.pack(), expected)

        ar2 = AuthResponse()
        ar2.unpack(ET.fromstring(expected))
        self.assertEqual(ar2.response, "hello")
        self.assertEqual(ar2.username, "rods")

    def test_inx_ival_pair(self):
        iip = IntegerIntegerMap()
        iip.iiLen = 2
        iip.inx = [4, 5]
        iip.ivalue = [1, 2]
        expected = "<InxIvalPair_PI>\
<iiLen>2</iiLen>\
<inx>4</inx>\
<inx>5</inx>\
<ivalue>1</ivalue>\
<ivalue>2</ivalue>\
</InxIvalPair_PI>"
        self.assertEqual(iip.pack(), expected)

        iip2 = IntegerIntegerMap()
        iip2.unpack(ET.fromstring(expected))
        self.assertEqual(iip2.iiLen, 2)
        self.assertEqual(iip2.inx, [4, 5])
        self.assertEqual(iip2.ivalue, [1, 2])

    def test_key_val_pair(self):
        kvp = StringStringMap()
        kvp.ssLen = 2
        kvp.keyWord = ["one", "two"]
        kvp.svalue = ["three", "four"]
        expected = "<KeyValPair_PI>\
<ssLen>2</ssLen>\
<keyWord>one</keyWord>\
<keyWord>two</keyWord>\
<svalue>three</svalue>\
<svalue>four</svalue>\
</KeyValPair_PI>"
        self.assertEqual(kvp.pack(), expected)

        kvp2 = StringStringMap()
        kvp2.unpack(ET.fromstring(expected))
        self.assertEqual(kvp2.ssLen, 2)
        self.assertEqual(kvp2.keyWord, ["one", "two"])
        self.assertEqual(kvp2.svalue, ["three", "four"])

    def test_gen_query_inp(self):
        gq = GenQueryRequest()
        gq.maxRows = 4
        gq.continueInx = 3
        gq.partialStartIndex = 2
        gq.options = 1

        kvp = StringStringMap()
        kvp.ssLen = 2
        kvp.keyWord = ['one', 'two']
        kvp.svalue = ['three', 'four']

        iip = IntegerIntegerMap()
        iip.iiLen = 2
        iip.inx = [4, 5]
        iip.ivalue = [1, 2]

        ivp = IntegerStringMap()
        ivp.isLen = 2
        ivp.inx = [1, 2]
        ivp.svalue = ['five', 'six']

        gq.KeyValPair_PI = kvp
        gq.InxIvalPair_PI = iip
        gq.InxValPair_PI = ivp

        expected = "<GenQueryInp_PI><maxRows>4</maxRows><continueInx>3</continueInx><partialStartIndex>2</partialStartIndex><options>1</options><KeyValPair_PI><ssLen>2</ssLen><keyWord>one</keyWord><keyWord>two</keyWord><svalue>three</svalue><svalue>four</svalue></KeyValPair_PI><InxIvalPair_PI><iiLen>2</iiLen><inx>4</inx><inx>5</inx><ivalue>1</ivalue><ivalue>2</ivalue></InxIvalPair_PI><InxValPair_PI><isLen>2</isLen><inx>1</inx><inx>2</inx><svalue>five</svalue><svalue>six</svalue></InxValPair_PI></GenQueryInp_PI>"
        self.assertEqual(gq.pack(), expected)

        gq2 = GenQueryRequest()
        gq2.unpack(ET.fromstring(expected))
        self.assertEqual(gq2.maxRows, 4)
        self.assertEqual(gq2.continueInx, 3)
        self.assertEqual(gq2.partialStartIndex, 2)
        self.assertEqual(gq2.options, 1)

        self.assertEqual(gq2.KeyValPair_PI.ssLen, 2)
        self.assertEqual(gq2.KeyValPair_PI.keyWord, ["one", "two"])
        self.assertEqual(gq2.KeyValPair_PI.svalue, ["three", "four"])

        self.assertEqual(gq2.InxIvalPair_PI.iiLen, 2)
        self.assertEqual(gq2.InxIvalPair_PI.inx, [4, 5])
        self.assertEqual(gq2.InxIvalPair_PI.ivalue, [1, 2])

        self.assertEqual(gq2.InxValPair_PI.isLen, 2)
        self.assertEqual(gq2.InxValPair_PI.inx, [1, 2])
        self.assertEqual(gq2.InxValPair_PI.svalue, ["five", "six"])

        self.assertEqual(gq2.pack(), expected)

    def test_sql_result(self):
        sr = GenQueryResponseColumn()
        sr.attriInx = 504
        sr.reslen = 64
        sr.value = ["one", "two"]

        expected = "<SqlResult_PI><attriInx>504</attriInx><reslen>64</reslen><value>one</value><value>two</value></SqlResult_PI>"
        self.assertEqual(sr.pack(), expected)

        sr2 = GenQueryResponseColumn()
        sr2.unpack(ET.fromstring(expected))
        self.assertEqual(sr2.attriInx, 504)
        self.assertEqual(sr2.reslen, 64)
        self.assertEqual(sr2.value, ["one", "two"])
        self.assertEqual(sr2.pack(), expected)

    def test_gen_query_out(self):
        gqo = GenQueryResponse()
        gqo.rowCnt = 2
        gqo.attriCnt = 2
        gqo.continueInx = 5
        gqo.totalRowCount = 7

        sr = GenQueryResponseColumn()
        sr.attriInx = 504
        sr.reslen = 64
        sr.value = ["one", "two"]
        gqo.SqlResult_PI = [sr, sr]

        expected = "<GenQueryOut_PI><rowCnt>2</rowCnt><attriCnt>2</attriCnt><continueInx>5</continueInx><totalRowCount>7</totalRowCount><SqlResult_PI><attriInx>504</attriInx><reslen>64</reslen><value>one</value><value>two</value></SqlResult_PI><SqlResult_PI><attriInx>504</attriInx><reslen>64</reslen><value>one</value><value>two</value></SqlResult_PI></GenQueryOut_PI>"
        self.assertEqual(gqo.pack(), expected)

        gqo2 = GenQueryResponse()
        gqo2.unpack(ET.fromstring(expected))

        self.assertEqual(gqo2.rowCnt, 2)
        self.assertEqual(gqo2.pack(), expected)

if __name__ == "__main__":
    unittest.main()
