"""
Contains the UCSC proxy
"""

from galaxy.web.base.controller import *

import sys
import json
from galaxy import web, util

import re, urllib, logging

log = logging.getLogger( __name__ )

class UCSCProxy( BaseUIController ):

    def create_display(self, store):
        """Creates a more meaningulf display name"""
        track  = store.get('hgta_track','no track')
        table  = store.get('hgta_table','no table')
        region = store.get('hgta_regionType','')
        if region not in [ 'genome', 'encode']:
            region = store.get('position','')
        if track == table:
            display = 'UCSC: %s (%s)' % (track, region)
        else:
            display = 'UCSC: %s, %s (%s)' % (track, table, region)
        return display

    @web.expose
    def index(self, trans, init=False, **kwd):
        base_url = None
        params = dict(kwd)
        try:
            store = params.get("__GALAXY__", None)
            if store:
                store = json.loads(util.string_to_object(store))
            else:
                store = {}
            UCSC_URL = 'UCSC_URL'
            base_url = store.get(UCSC_URL, "http://genome.ucsc.edu/cgi-bin/hgTables?")
            params   = dict(kwd)
            params['init'] = init

            if not init:
                for key, value in kwd.items():
                    store[key] = value
                try: del store["__GALAXY__"]
                except: pass
            else:
                store = {}

            if init == "1":
                base_url = "http://genome.ucsc.edu/cgi-bin/hgTables?"
                params['db'] = 'hg17'
            if init == "2":
                base_url = "http://genome-test.cse.ucsc.edu/cgi-bin/hgTables?"
                params['db'] = 'hg17'
            if init == "3":
                base_url = "http://archaea.ucsc.edu/cgi-bin/hgTables?"

            store[UCSC_URL] = base_url

            try: del params["__GALAXY__"]
            except: pass
            url = base_url + urllib.urlencode(params)

            page = urllib.urlopen(url)
            content = page.info().get('Content-type', '')
        except Exception, exc:
            trans.log_event( "Proxy Error -> %s" % str(exc) )
            msg = 'There has been a problem connecting to <i>%s</i> <p> <b>%s<b>' % (base_url, exc)
            return msg

        if content.startswith('text/plain'):
            params['display'] = self.create_display(store)
            params['dbkey']   = store.get('db', '*')
            params['tool_id'] = 'ucsc_proxy'
            params['proxy_url'] = base_url
            params['runtool_btn'] = 'T'
            #url = "/echo?" + urllib.urlencode(params)
            url = "/tool_runner/index?" + urllib.urlencode(params)
            trans.response.send_redirect(url)
        else:
            try:
                text = page.read()

                # Serialize store into a form element
                store_text = "<INPUT TYPE=\"HIDDEN\" NAME=\"__GALAXY__\" ID=\"__GALAXY__\" VALUE=\"" \
                             + json.dumps(util.object_to_string(store)) + "\" \>"

                # Remove text regions that should not be exposed
                for key,value in altered_regions.items():
                    text = text.replace(key,value)
                # Capture only the forms
                newtext = beginning
                for form in re.finditer("(?s)(<FORM.*?)(</FORM>)",text):
                    newtext = newtext + form.group(1) + store_text + form.group(2)
                if 'hgta_doLookupPosition' in params:
                    lookup = re.search("(?s).*?(<H2>.*</PRE>)",text)
                    if lookup:
                        newtext = newtext + lookup.group(1)
                # if these keys are in the params, then pass the content through
                passthruContent = ['hgta_doSummaryStats', 'hgta_doSchema', 'hgta_doSchemaDb']
                for k in passthruContent:
                    if k in params:
                        content = re.search("(?s)CONTENT TABLES.*?-->(.*/TABLE>)",text)
                        if content:
                            newtext = newtext + "<TABLE>" + content.group(1)

                newtext = newtext + ending
                return newtext
            except KeyError, exc:
                log.error(str(exc))
                trans.log_event( "Proxy Error -> %s" % str(exc) )
                msg = 'There has been a problem connecting to <i>%s</i> <p> <b>%s<b>' % (base_url, exc)
                return msg

# HTML for generating the proxy page.
beginning = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>

<head>
<title>Galaxy</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link href="/static/style/base.css" rel="stylesheet" type="text/css" />
<script language="javascript" type="text/javascript">
function changeTarget(target)
{
    document.forms['mainForm'].target = target;
}
</script>
</head>

<body>
<div class="toolForm" id="ucsc_proxy">
  <div class="toolFormTitle">UCSC Table Browser</div>

  <div class="toolFormBody">
 '''
ending = '''
<P>This is a proxy to the data services provided by the <a href=\"http://genome.ucsc.edu\" target=\"_blank\">UCSC Genome Browser</a>'s <a href=\"http://genome.ucsc.edu/cgi-bin/hgTables\" target=\"_blank\">Table Browser.</a></P>
  </div>
</div>
</body>
</html>'''

# This is a mess of mappings of text to make the proxy friendlier to
# galaxy users.
altered_regions = {
        '"../cgi-bin/hgTables' : '"/ucsc_proxy/index',
        '<TR><TD>\n<B>output file:</B>&nbsp;<INPUT TYPE=TEXT NAME="hgta_outFileName" SIZE=29 VALUE="">&nbsp;(leave blank to keep output in browser)</TD></TR>\n<TR><TD>\n<B>file type returned:&nbsp;</B><INPUT TYPE=RADIO NAME="hgta_compressType" VALUE="none" CHECKED>&nbsp;plain text&nbsp&nbsp<INPUT TYPE=RADIO NAME="hgta_compressType" VALUE="gzip" >&nbsp;gzip compressed</TD></TR>' : '<INPUT TYPE=HIDDEN NAME="hgta_compressType" VALUE="none" /><INPUT TYPE=HIDDEN NAME="hgta_outFileName" VALUE="" />',
        ' <P>To reset <B>all</B> user cart settings (including custom tracks), \n<A HREF="/cgi-bin/cartReset?destination=/cgi-bin/hgTables">click here</A>.' : '',
        'ACTION="../cgi-bin/hgTables"' : 'ACTION="/ucsc_proxy/index"',
        '<A HREF="/goldenPath/help/customTrack.html" TARGET=_blank>custom track</A>' : '<A HREF="http://genome.ucsc.edu/goldenPath/help/customTrack.html" TARGET=_blank>custom track</A>',
        '<INPUT TYPE=RADIO NAME="hgta_regionType" VALUE="genome" onClick="regionType=\'genome\';" CHECKED>' : '<INPUT TYPE=RADIO NAME="hgta_regionType" VALUE="genome" onClick="regionType=\'genome\';">',
        '<INPUT TYPE=RADIO NAME="hgta_regionType" VALUE="range" onClick="regionType=\'range\';">' : '<INPUT TYPE=RADIO NAME="hgta_regionType" VALUE="range" onClick="regionType=\'range\';" CHECKED>',
        "<OPTION VALUE=bed>" : "<OPTION VALUE=bed SELECTED>" ,
        '<INPUT TYPE=SUBMIT NAME="hgta_doSchema" VALUE="describe table schema">' : '<INPUT TYPE=SUBMIT NAME="hgta_doSchema" VALUE="describe table schema" onClick="changeTarget(\'_blank\')" onMouseOut="changeTarget(\'_self\')">'
        }
