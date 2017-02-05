#!/usr/bin/env python
"""
check_galaxy can be run by hand, although it is meant to run from cron
via the check_galaxy.sh script in Galaxy's cron/ directory.
"""
from __future__ import print_function

import filecmp
import formatter
import getopt
import htmllib
import json
import os
import socket
import sys
import tempfile
import time
import warnings

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import twill
    import twill.commands as tc

# options
if "DEBUG" in os.environ:
    debug = os.environ["DEBUG"]
else:
    debug = False

test_data_dir = os.path.join( os.path.dirname( __file__ ), 'check_galaxy_data' )
# what tools to run - not so pretty
tools = {
    "Extract+genomic+DNA+1":
    [
        {
            "inputs":
            (
                {
                    "file_path": os.path.join( test_data_dir, "1.bed" ),
                    "dbkey": "hg17",
                },

            )
        },
        { "check_file": os.path.join( test_data_dir, "extract_genomic_dna_out1.fasta" ) },
        {
            "tool_run_options":
            {
                "input": "1.bed",
                "interpret_features": "yes",
                "index_source": "cached",
                "out_format": "fasta"
            }
        }
    ]
}


# handle arg(s)
def usage():
    sys.exit("usage: check_galaxy.py <server> <username> <password>")


try:
    opts, args = getopt.getopt( sys.argv[1:], 'n' )
except getopt.GetoptError as e:
    print(str(e))
    usage()
if len( args ) < 1:
    usage()
server = args[0]
username = args[1]
password = args[2]

new_history = False
for o, a in opts:
    if o == "-n":
        if debug:
            print("Specified -n, will create a new history")
        new_history = True
    else:
        usage()

# state information
var_dir = os.path.join( os.path.expanduser('~'), ".check_galaxy", server )
if not os.access( var_dir, os.F_OK ):
    os.makedirs( var_dir, 0o700 )

# default timeout for twill browser is never
socket.setdefaulttimeout(300)

# user-agent
tc.agent("Mozilla/5.0 (compatible; check_galaxy/0.1)")
tc.config('use_tidy', 0)


class Browser:
    def __init__(self):
        self.server = server
        self.tool = None
        self.tool_opts = None
        self._hda_id = None
        self._hda_state = None
        self._history_id = None
        self.check_file = None
        self.cookie_jar = os.path.join( var_dir, "cookie_jar" )
        dprint("cookie jar path: %s" % self.cookie_jar)
        if not os.access(self.cookie_jar, os.R_OK):
            dprint("no cookie jar at above path, creating")
            tc.save_cookies(self.cookie_jar)
        tc.load_cookies(self.cookie_jar)

    def get(self, path):
        tc.go("http://%s%s" % (self.server, path))
        tc.code(200)

    def reset(self):
        self.tool = None
        self.tool_opts = None
        self._hda_id = None
        self._hda_state = None
        self._history_id = None
        self.check_file = None
        if new_history:
            self.get("/history/delete_current")
            tc.save_cookies(self.cookie_jar)
        self.delete_datasets()

    def check_redir(self, url):
        try:
            tc.get_browser()._browser.set_handle_redirect(False)
            tc.go(url)
            tc.code(302)
            tc.get_browser()._browser.set_handle_redirect(True)
            dprint( "%s is returning redirect (302)" % url )
            return(True)
        except twill.errors.TwillAssertionError as e:
            tc.get_browser()._browser.set_handle_redirect(True)
            dprint( "%s is not returning redirect (302): %s" % (url, e) )
            code = tc.browser.get_code()
            if code == 502:
                sys.exit("Galaxy is down (code 502)")
            return False

    def login(self, user, pw):
        self.get("/user/login")
        tc.fv("1", "email", user)
        tc.fv("1", "password", pw)
        tc.submit("Login")
        tc.code(200)
        if len(tc.get_browser().get_all_forms()) > 0:
            # uh ohs, fail
            p = userParser()
            p.feed(tc.browser.get_html())
            if p.no_user:
                dprint("user does not exist, will try creating")
                self.create_user(user, pw)
            elif p.bad_pw:
                raise Exception("Password is incorrect")
            else:
                raise Exception("Unknown error logging in")
        tc.save_cookies(self.cookie_jar)

    def create_user(self, user, pw):
        self.get("/user/create")
        tc.fv("1", "email", user)
        tc.fv("1", "password", pw)
        tc.fv("1", "confirm", pw)
        tc.submit("Submit")
        tc.code(200)
        if len(tc.get_browser().get_all_forms()) > 0:
            p = userParser()
            p.feed(tc.browser.get_html())
            if p.already_exists:
                raise Exception('The user you were trying to create already exists')

    def upload(self, input):
        self.get("/tool_runner/index?tool_id=upload1")
        tc.fv("1", "file_type", "bed")
        tc.fv("1", "dbkey", input.get('dbkey', '?'))
        tc.formfile("1", "file_data", input['file_path'])
        tc.submit("runtool_btn")
        tc.code(200)

    def runtool(self):
        self.get("/tool_runner/index?tool_id=%s" % self.tool)
        for k, v in self.tool_opts.items():
            tc.fv("1", k, v)
        tc.submit("runtool_btn")
        tc.code(200)

    @property
    def history_id(self):
        if self._history_id is None:
            self.get('/api/histories')
            self._history_id = json.loads(tc.browser.get_html())[0]['id']
        return self._history_id

    @property
    def history_contents(self):
        self.get('/api/histories/%s/contents' % self.history_id)
        return json.loads(tc.browser.get_html())

    @property
    def hda_id(self):
        if self._hda_id is None:
            self.set_top_hda()
        return self._hda_id

    @property
    def hda_state(self):
        if self._hda_state is None:
            self.set_top_hda()
        return self._hda_state

    def set_top_hda(self):
        self.get(self.history_contents[-1]['url'])
        hda = json.loads(tc.browser.get_html())
        self._hda_id = hda['id']
        self._hda_state = hda['state']

    @property
    def undeleted_hdas(self):
        rval = []
        for item in self.history_contents:
            self.get(item['url'])
            hda = json.loads(tc.browser.get_html())
            if hda['deleted'] is False:
                rval.append(hda)
        return rval

    @property
    def history_state(self):
        self.get('/api/histories/%s' % self.history_id)
        return json.loads(tc.browser.get_html())['state']

    @property
    def history_state_terminal(self):
        if self.history_state not in ['queued', 'running', 'paused']:
            return True
        return False

    def wait(self):
        sleep_amount = 1
        count = 0
        maxiter = 16
        while count < maxiter:
            count += 1
            if not self.history_state_terminal:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        if count == maxiter:
            raise Exception("Tool never finished")

    def check_state(self):
        if self.hda_state != "ok":
            self.get("/datasets/%s/stderr" % self.hda_id)
            print(tc.browser.get_html())
            raise Exception("HDA %s NOT OK: %s" % (self.hda_id, self.hda_state))

    def diff(self):
        self.get("/datasets/%s/display?to_ext=%s" % (self.hda_id, self.tool_opts.get('out_format', 'fasta')))
        data = tc.browser.get_html()
        tmp = tempfile.mkstemp()
        dprint("tmp file: %s" % tmp[1])
        tmpfh = os.fdopen(tmp[0], 'w')
        tmpfh.write(data)
        tmpfh.close()
        if filecmp.cmp(tmp[1], self.check_file):
            dprint("Tool output is as expected")
        else:
            if not debug:
                os.remove(tmp[1])
            raise Exception("Tool output differs from expected")
        if not debug:
            os.remove(tmp[1])

    def delete_datasets(self):
        for hda in self.undeleted_hdas:
            self.get('/datasets/%s/delete' % hda['id'])
        hdas = [hda['id'] for hda in self.undeleted_hdas]
        if hdas:
            print("Remaining datasets ids:", " ".join(hdas))
            raise Exception("History still contains datasets after attempting to delete them")

    def check_if_logged_in(self):
        self.get("/user?cntrller=user")
        p = loggedinParser()
        p.feed(tc.browser.get_html())
        return p.logged_in


class userParser(htmllib.HTMLParser):
    def __init__(self):
        htmllib.HTMLParser.__init__(self, formatter.NullFormatter())
        self.in_span = False
        self.in_div = False
        self.no_user = False
        self.bad_pw = False
        self.already_exists = False

    def start_span(self, attrs):
        self.in_span = True

    def start_div(self, attrs):
        self.in_div = True

    def end_span(self):
        self.in_span = False

    def end_div(self):
        self.in_div = False

    def handle_data(self, data):
        if self.in_span or self.in_div:
            if data == "No such user (please note that login is case sensitive)":
                self.no_user = True
            elif data == "Invalid password":
                self.bad_pw = True
            elif data == "User with that email already exists":
                self.already_exists = True


class loggedinParser(htmllib.HTMLParser):
    def __init__(self):
        htmllib.HTMLParser.__init__(self, formatter.NullFormatter())
        self.in_p = False
        self.logged_in = False

    def start_p(self, attrs):
        self.in_p = True

    def end_p(self):
        self.in_p = False

    def handle_data(self, data):
        if self.in_p:
            if data == "You are currently not logged in.":
                self.logged_in = False
            elif data.startswith( "You are currently logged in as " ):
                self.logged_in = True


def dprint(str):
    if debug:
        print(str)


if __name__ == "__main__":

    dprint("checking %s" % server)

    b = Browser()

    # login (or not)
    if b.check_if_logged_in():
        dprint("we are already logged in (via cookies), hooray!")
    else:
        dprint("not logged in... logging in")
        b.login(username, password)

    for tool, params in tools.items():

        check_file = ""

        # make sure history and state is clean
        b.reset()
        b.tool = tool

        # get all the tool run conditions
        for dict in params:
            for k, v in dict.items():
                if k == 'inputs':
                    for input in v:
                        b.upload(input)
                    b.wait()
                elif k == 'check_file':
                    b.check_file = v
                elif k == 'tool_run_options':
                    b.tool_opts = v
                else:
                    raise Exception("Unknown key in tools dict: %s" % k)

        b.runtool()
        b.wait()
        b.check_state()
        b.diff()
        b.delete_datasets()

    print("OK")
    sys.exit(0)
