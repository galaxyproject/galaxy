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
import os
import socket
import sys
import tempfile
import time

import twill
import twill.commands as tc

# options
if "DEBUG" in os.environ:
    debug = os.environ["DEBUG"]
else:
    debug = False
scripts_dir = os.path.abspath( os.path.dirname( sys.argv[0] ) )
test_data_dir = os.path.join( scripts_dir, os.pardir, "test-data" )
# what tools to run - not so pretty
tools = {
    "gops_intersect_1":
    [
        {
            "inputs":
            (
                os.path.join( test_data_dir, "1.bed" ),
                os.path.join( test_data_dir, "2.bed" )
            )
        },
        { "check_file": os.path.join( test_data_dir, "gops_intersect_out.bed" ) },
        {
            "tool_run_options":
            {
                "input1": "1.bed",
                "input2": "2.bed",
                "min": "1",
                "returntype": ""
            }
        }
    ]
}


# handle arg(s)
def usage():
    sys.exit("usage: check_galaxy.py <server>")


try:
    opts, args = getopt.getopt( sys.argv[1:], 'n' )
except getopt.GetoptError as e:
    print(str(e))
    usage()
if len( args ) < 1:
    usage()
server = args[0]
if server.endswith(".g2.bx.psu.edu"):
    if debug:
        print("Checking a PSU Galaxy server, using maint file")
    maint = "/errordocument/502/%s/maint" % args[0].split('.', 1)[0]
else:
    maint = None
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

# get user/pass
login_file = os.path.join( var_dir, "login" )
try:
    f = open( login_file, 'r' )
except:
    message = """Please create the file:
%s
This should contain a username and password to log in to Galaxy with,
on one line, separated by whitespace, e.g.:

check_galaxy@example.com password

If the user does not exist, check_galaxy will create it for you.""" % login_file
    sys.exit(message)
( username, password ) = f.readline().split()

# default timeout for twill browser is never
socket.setdefaulttimeout(300)

# user-agent
tc.agent("Mozilla/5.0 (compatible; check_galaxy/0.1)")
tc.config('use_tidy', 0)


class Browser:

    def __init__(self):
        self.server = server
        self.maint = maint
        self.tool = None
        self.tool_opts = None
        self.id = None
        self.status = None
        self.check_file = None
        self.hid = None
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
        self.id = None
        self.status = None
        self.check_file = None
        self.delete_datasets()
        self.get("/root/history")
        p = didParser()
        p.feed(tc.browser.get_html())
        if len(p.dids) > 0:
            print("Remaining datasets ids:", " ".join( p.dids ))
            raise Exception("History still contains datasets after attempting to delete them")
        if new_history:
            self.get("/history/delete_current")
            tc.save_cookies(self.cookie_jar)

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
                is_maint = self.check_maint()
                if is_maint:
                    dprint( "Galaxy is down, but a maint file was found, so not sending alert" )
                    sys.exit(0)
                else:
                    sys.exit("Galaxy is down (code 502)")
            return(False)

    # checks for a maint file
    def check_maint(self):
        if self.maint is None:
            # dprint( "Warning: unable to check maint file for %s" % self.server )
            return(False)
        try:
            self.get(self.maint)
            return(True)
        except twill.errors.TwillAssertionError:
            return(False)

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

    def upload(self, file):
        self.get("/tool_runner/index?tool_id=upload1")
        tc.fv("1", "file_type", "bed")
        tc.formfile("1", "file_data", file)
        tc.submit("runtool_btn")
        tc.code(200)

    def runtool(self):
        self.get("/tool_runner/index?tool_id=%s" % self.tool)
        for k, v in self.tool_opts.items():
            tc.fv("1", k, v)
        tc.submit("runtool_btn")
        tc.code(200)

    def wait(self):
        sleep_amount = 1
        count = 0
        maxiter = 16
        while count < maxiter:
            count += 1
            self.get("/root/history")
            page = tc.browser.get_html()
            if page.find( '<!-- running: do not change this comment, used by TwillTestCase.wait -->' ) > -1:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        if count == maxiter:
            raise Exception("Tool never finished")

    def check_status(self):
        self.get("/root/history")
        p = historyParser()
        p.feed(tc.browser.get_html())
        if p.status != "ok":
            raise Exception("JOB %s NOT OK: %s" % (p.id, p.status))
        self.id = p.id
        self.status = p.status
        # return((p.id, p.status))

    def diff(self):
        self.get("/datasets/%s/display/display?to_ext=bed" % self.id)
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
        self.get("/root/history")
        p = didParser()
        p.feed(tc.browser.get_html())
        dids = p.dids
        for did in dids:
            self.get("/datasets/%s/delete" % did)

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


class historyParser(htmllib.HTMLParser):
    def __init__(self):
        htmllib.HTMLParser.__init__(self, formatter.NullFormatter())
        self.status = None
        self.id = None

    def start_div(self, attrs):
        # find the top history item
        for i in attrs:
            if i[0] == "class" and i[1].startswith("historyItemWrapper historyItem historyItem-"):
                self.status = i[1].rsplit("historyItemWrapper historyItem historyItem-", 1)[1]
                dprint("status: %s" % self.status)
            if i[0] == "id" and i[1].startswith("historyItem-"):
                self.id = i[1].rsplit("historyItem-", 1)[1]
                dprint("id: %s" % self.id)
        if self.status is not None:
            self.reset()


class didParser(htmllib.HTMLParser):
    def __init__(self):
        htmllib.HTMLParser.__init__(self, formatter.NullFormatter())
        self.dids = []

    def start_div(self, attrs):
        for i in attrs:
            if i[0] == "id" and i[1].startswith("historyItemContainer-"):
                self.dids.append( i[1].rsplit("historyItemContainer-", 1)[1] )
                dprint("got a dataset id: %s" % self.dids[-1])


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
                    for file in v:
                        b.upload(file)
                elif k == 'check_file':
                    b.check_file = v
                elif k == 'tool_run_options':
                    b.tool_opts = v
                else:
                    raise Exception("Unknown key in tools dict: %s" % k)

        b.runtool()
        b.wait()
        b.check_status()
        b.diff()
        b.delete_datasets()

        # by this point, everything else has succeeded.  there should be no maint.
        is_maint = b.check_maint()
        if is_maint:
            sys.exit("Galaxy is up and fully functional, but a maint file is in place.")

    sys.exit(0)
