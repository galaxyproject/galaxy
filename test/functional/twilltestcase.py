from __future__ import print_function

import logging
import os
import tempfile
from json import loads
from xml.etree import ElementTree

# Be sure to use Galaxy's vanilla pyparsing instead of the older version
# imported by twill.
import pyparsing  # noqa: F401
import twill
import twill.commands as tc
from six import string_types, StringIO
from six.moves.urllib.parse import urlencode, urlparse
from twill.other_packages._mechanize_dist import ClientForm

from base.testcase import FunctionalTestCase  # noqa: I100,I201,I202
from galaxy.util import unicodify  # noqa: I201

# Force twill to log to a buffer -- FIXME: Should this go to stdout and be captured by nose?
buffer = StringIO()
twill.set_output(buffer)
tc.config('use_tidy', 0)

# Dial ClientCookie logging down (very noisy)
logging.getLogger("ClientCookie.cookies").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

DEFAULT_TOOL_TEST_WAIT = os.environ.get("GALAXY_TEST_DEFAULT_WAIT", 86400)


class TwillTestCase(FunctionalTestCase):

    """Class of FunctionalTestCase geared toward HTML interactions using the Twill library."""

    def check_for_strings(self, strings_displayed=[], strings_not_displayed=[]):
        if strings_displayed:
            for string in strings_displayed:
                self.check_page_for_string(string)
        if strings_not_displayed:
            for string in strings_not_displayed:
                self.check_string_not_in_page(string)

    def check_history_for_exact_string(self, string, show_deleted=False):
        """Looks for exact match to 'string' in history page"""
        params = dict()
        if show_deleted:
            params['show_deleted'] = True
        self.visit_url("/history", params=params)
        try:
            tc.find(string)
        except Exception:
            fname = self.write_temp_file(tc.browser.get_html())
            errmsg = "no match to '%s'\npage content written to '%s'" % (string, fname)
            raise AssertionError(errmsg)

    def check_page(self, strings_displayed, strings_displayed_count, strings_not_displayed):
        """Checks a page for strings displayed, not displayed and number of occurrences of a string"""
        for check_str in strings_displayed:
            self.check_page_for_string(check_str)
        for check_str, count in strings_displayed_count:
            self.check_string_count_in_page(check_str, count)
        for check_str in strings_not_displayed:
            self.check_string_not_in_page(check_str)

    def check_page_for_string(self, patt):
        """Looks for 'patt' in the current browser page"""
        page = unicodify(self.last_page())
        if page.find(patt) == -1:
            fname = self.write_temp_file(page)
            errmsg = "no match to '%s'\npage content written to '%s'\npage: [[%s]]" % (patt, fname, page)
            raise AssertionError(errmsg)

    def check_string_count_in_page(self, patt, min_count):
        """Checks the number of 'patt' occurrences in the current browser page"""
        page = self.last_page()
        patt_count = page.count(patt)
        # The number of occurrences of patt in the page should be at least min_count
        # so show error if patt_count is less than min_count
        if patt_count < min_count:
            fname = self.write_temp_file(page)
            errmsg = "%i occurrences of '%s' found instead of %i.\npage content written to '%s' " % (min_count, patt, patt_count, fname)
            raise AssertionError(errmsg)

    def check_string_not_in_page(self, patt):
        """Checks to make sure 'patt' is NOT in the page."""
        page = self.last_page()
        if page.find(patt) != -1:
            fname = self.write_temp_file(page)
            errmsg = "string (%s) incorrectly displayed in page.\npage content written to '%s'" % (patt, fname)
            raise AssertionError(errmsg)

    # Functions associated with user accounts

    def create(self, cntrller='user', email='test@bx.psu.edu', password='testuser', username='admin-user', redirect=''):
        # HACK: don't use panels because late_javascripts() messes up the twill browser and it
        # can't find form fields (and hence user can't be logged in).
        params = dict(cntrller=cntrller, use_panels=False)
        self.visit_url("/user/create", params)
        tc.fv('registration', 'email', email)
        tc.fv('registration', 'redirect', redirect)
        tc.fv('registration', 'password', password)
        tc.fv('registration', 'confirm', password)
        tc.fv('registration', 'username', username)
        tc.submit('create_user_button')
        previously_created = False
        username_taken = False
        invalid_username = False
        try:
            self.check_page_for_string("Created new user account")
        except Exception:
            try:
                # May have created the account in a previous test run...
                self.check_page_for_string("User with that email already exists")
                previously_created = True
            except Exception:
                try:
                    self.check_page_for_string('Public name is taken; please choose another')
                    username_taken = True
                except Exception:
                    try:
                        # Note that we're only checking if the usr name is >< 4 chars here...
                        self.check_page_for_string('Public name must be at least 4 characters in length')
                        invalid_username = True
                    except Exception:
                        pass
        return previously_created, username_taken, invalid_username

    def get_all_history_ids_from_api(self):
        return [history['id'] for history in self.json_from_url('/api/histories')]

    def get_form_controls(self, form):
        formcontrols = []
        for i, control in enumerate(form.controls):
            formcontrols.append("control %d: %s" % (i, str(control)))
        return formcontrols

    def get_hids_in_history(self, history_id):
        """Returns the list of hid values for items in a history"""
        hids = []
        api_url = '/api/histories/%s/contents' % history_id
        hids = [history_item['hid'] for history_item in self.json_from_url(api_url)]
        return hids

    def get_history_as_data_list(self, show_deleted=False):
        """Returns the data elements of a history"""
        tree = self.history_as_xml_tree(show_deleted=show_deleted)
        data_list = [elem for elem in tree.findall("data")]
        return data_list

    def get_history_from_api(self, encoded_history_id=None, show_deleted=None, show_details=False):
        if encoded_history_id is None:
            history = self.get_latest_history()
            encoded_history_id = history['id']
        params = dict()
        if show_deleted is not None:
            params['deleted'] = show_deleted
        api_url = '/api/histories/%s/contents' % encoded_history_id
        json_data = self.json_from_url(api_url, params=params)
        if show_deleted is not None:
            hdas = []
            for hda in json_data:
                if show_deleted:
                    hdas.append(hda)
                else:
                    if not hda['deleted']:
                        hdas.append(hda)
            json_data = hdas
        if show_details:
            params['details'] = ','.join([hda['id'] for hda in json_data])
            api_url = '/api/histories/%s/contents' % encoded_history_id
            json_data = self.json_from_url(api_url, params=params)
        return json_data

    def get_latest_history(self):
        return self.json_from_url('/api/histories')[0]

    def get_running_datasets(self):
        self.visit_url('/api/histories')
        history_id = loads(self.last_page())[0]['id']
        self.visit_url('/api/histories/%s' % history_id)
        jsondata = loads(self.last_page())
        return jsondata['state'] in ['queued', 'running']

    def history_as_xml_tree(self, show_deleted=False):
        """Returns a parsed xml object of a history"""
        params = {
            'as_xml': True,
            'show_deleted': show_deleted
        }
        self.visit_url('/history', params=params)
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def is_history_empty(self):
        """
        Uses history page JSON to determine whether this history is empty
        (i.e. has no undeleted datasets).
        """
        return len(self.get_history_from_api()) == 0

    def json_from_url(self, url, params={}):
        self.visit_url(url, params)
        return loads(self.last_page())

    def last_page(self):
        """
        Return the last visited page (usually HTML, but can binary data as
        well).
        """
        return tc.browser.get_html()

    def last_url(self):
        return tc.browser.get_url()

    def login(self, email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='', logout_first=True):
        # Clear cookies.
        if logout_first:
            self.logout()
        # test@bx.psu.edu is configured as an admin user
        previously_created, username_taken, invalid_username = \
            self.create(email=email, password=password, username=username, redirect=redirect)
        if previously_created:
            # The acount has previously been created, so just login.
            # HACK: don't use panels because late_javascripts() messes up the twill browser and it
            # can't find form fields (and hence user can't be logged in).
            params = {
                'use_panels': False
            }
            self.visit_url('/user/login', params=params)
            self.submit_form('login', 'login_button', login=email, redirect=redirect, password=password)

    def logout(self):
        self.visit_url("%s/user/logout" % self.url)
        self.check_page_for_string("You have been logged out")
        tc.browser.cj.clear()

    def new_history(self, name=None):
        """Creates a new, empty history"""
        params = dict()
        if name:
            params['name'] = name
        self.visit_url("%s/history_new" % self.url, params=params)
        self.check_page_for_string('New history created')
        assert self.is_history_empty(), 'Creating new history did not result in an empty history.'

    def refresh_form(self, control_name, value, form_no=0, form_id=None, form_name=None, **kwd):
        """Handles Galaxy's refresh_on_change for forms without ultimately submitting the form"""
        # control_name is the name of the form field that requires refresh_on_change, and value is
        # the value to which that field is being set.
        for i, f in enumerate(self.showforms()):
            if i == form_no or (form_id is not None and f.id == form_id) or (form_name is not None and f.name == form_name):
                break
        formcontrols = self.get_form_controls(f)
        try:
            control = f.find_control(name=control_name)
        except Exception:
            log.debug('\n'.join(formcontrols))
            # This assumes we always want the first control of the given name, which may not be ideal...
            control = f.find_control(name=control_name, nr=0)
        # Check for refresh_on_change attribute, submit a change if required
        if 'refresh_on_change' in control.attrs.keys():
            # Clear Control and set to proper value
            control.clear()
            tc.fv(f.name, control.name, value)
            # Create a new submit control, allows form to refresh, instead of going to next page
            control = ClientForm.SubmitControl('SubmitControl', '___refresh_grouping___', {'name': 'refresh_grouping'})
            control.add_to_form(f)
            control.fixup()
            # Submit for refresh
            tc.submit('___refresh_grouping___')

    def showforms(self):
        """Shows form, helpful for debugging new tests"""
        return tc.showforms()

    def submit_form(self, form_no=0, button="runtool_btn", **kwd):
        """Populates and submits a form from the keyword arguments."""
        # An HTMLForm contains a sequence of Controls.  Supported control classes are:
        # TextControl, FileControl, ListControl, RadioControl, CheckboxControl, SelectControl,
        # SubmitControl, ImageControl
        for i, f in enumerate(self.showforms()):
            if i == form_no:
                break
        # To help with debugging a tool, print out the form controls when the test fails
        print("form '%s' contains the following controls ( note the values )" % f.name)
        controls = {}
        formcontrols = self.get_form_controls(f)
        hc_prefix = '<HiddenControl('
        for i, control in enumerate(f.controls):
            if hc_prefix not in str(control):
                try:
                    # check if a repeat element needs to be added
                    if control.name is not None:
                        if control.name not in kwd and control.name.endswith('_add'):
                            # control name doesn't exist, could be repeat
                            repeat_startswith = control.name[0:-4]
                            if repeat_startswith and not [c_name for c_name in controls.keys() if c_name.startswith(repeat_startswith)] and [c_name for c_name in kwd.keys() if c_name.startswith(repeat_startswith)]:
                                tc.browser.clicked(f, control)
                                tc.submit(control.name)
                                return self.submit_form(form_no=form_no, button=button, **kwd)
                    # Check for refresh_on_change attribute, submit a change if required
                    if hasattr(control, 'attrs') and 'refresh_on_change' in control.attrs.keys():
                        changed = False
                        # For DataToolParameter, control.value is the HDA id, but kwd contains the filename.
                        # This loop gets the filename/label for the selected values.
                        item_labels = [item.attrs['label'] for item in control.get_items() if item.selected]
                        for value in kwd[control.name]:
                            if value not in control.value and True not in [value in item_label for item_label in item_labels]:
                                changed = True
                                break
                        if changed:
                            # Clear Control and set to proper value
                            control.clear()
                            # kwd[control.name] should be a singlelist
                            for elem in kwd[control.name]:
                                tc.fv(f.name, control.name, str(elem))
                            # Create a new submit control, allows form to refresh, instead of going to next page
                            control = ClientForm.SubmitControl('SubmitControl', '___refresh_grouping___', {'name': 'refresh_grouping'})
                            control.add_to_form(f)
                            control.fixup()
                            # Submit for refresh
                            tc.submit('___refresh_grouping___')
                            return self.submit_form(form_no=form_no, button=button, **kwd)
                except Exception:
                    log.exception("In submit_form, continuing, but caught exception.")
                    for formcontrol in formcontrols:
                        log.debug(formcontrol)
                    continue
                controls[control.name] = control
        # No refresh_on_change attribute found in current form, so process as usual
        for control_name, control_value in kwd.items():
            if control_name not in controls:
                continue  # these cannot be handled safely - cause the test to barf out
            if not isinstance(control_value, list):
                control_value = [control_value]
            control = controls[control_name]
            control.clear()
            if control.is_of_kind("text"):
                tc.fv(f.name, control.name, ",".join(control_value))
            elif control.is_of_kind("list"):
                try:
                    if control.is_of_kind("multilist"):
                        if control.type == "checkbox":
                            def is_checked(value):
                                # Copied from form_builder.CheckboxField
                                if value is True:
                                    return True
                                if isinstance(value, list):
                                    value = value[0]
                                return isinstance(value, string_types) and value.lower() in ("yes", "true", "on")
                            try:
                                checkbox = control.get()
                                checkbox.selected = is_checked(control_value)
                            except Exception as e1:
                                print("Attempting to set checkbox selected value threw exception: ", e1)
                                # if there's more than one checkbox, probably should use the behaviour for
                                # ClientForm.ListControl ( see twill code ), but this works for now...
                                for elem in control_value:
                                    control.get(name=elem).selected = True
                        else:
                            for elem in control_value:
                                try:
                                    # Doubt this case would ever work, but want
                                    # to preserve backward compat.
                                    control.get(name=elem).selected = True
                                except Exception:
                                    # ... anyway this is really what we want to
                                    # do, probably even want to try the len(
                                    # elem ) > 30 check below.
                                    control.get(label=elem).selected = True
                    else:  # control.is_of_kind( "singlelist" )
                        for elem in control_value:
                            try:
                                tc.fv(f.name, control.name, str(elem))
                            except Exception:
                                try:
                                    # Galaxy truncates long file names in the dataset_collector in galaxy/tools/parameters/basic.py
                                    if len(elem) > 30:
                                        elem_name = '%s..%s' % (elem[:17], elem[-11:])
                                        tc.fv(f.name, control.name, str(elem_name))
                                        pass
                                    else:
                                        raise
                                except Exception:
                                    raise
                            except Exception:
                                for formcontrol in formcontrols:
                                    log.debug(formcontrol)
                                log.exception("Attempting to set control '%s' to value '%s' (also tried '%s') threw exception.", control.name, elem, elem_name)
                                pass
                except Exception as exc:
                    for formcontrol in formcontrols:
                        log.debug(formcontrol)
                    errmsg = "Attempting to set field '%s' to value '%s' in form '%s' threw exception: %s\n" % (control_name, str(control_value), f.name, str(exc))
                    errmsg += "control: %s\n" % str(control)
                    errmsg += "If the above control is a DataToolparameter whose data type class does not include a sniff() method,\n"
                    errmsg += "make sure to include a proper 'ftype' attribute to the tag for the control within the <test> tag set.\n"
                    raise AssertionError(errmsg)
            else:
                # Add conditions for other control types here when necessary.
                pass
        tc.submit(button)

    def switch_history(self, id='', name=''):
        """Switches to a history in the current list of histories"""
        params = dict(operation='switch', id=id)
        self.visit_url("/history/list", params)
        if name:
            self.check_history_for_exact_string(name)

    def visit_url(self, url, params=None, doseq=False, allowed_codes=[200]):
        if params is None:
            params = dict()
        parsed_url = urlparse(url)
        if len(parsed_url.netloc) == 0:
            url = 'http://%s:%s%s' % (self.host, self.port, parsed_url.path)
        else:
            url = '%s://%s%s' % (parsed_url.scheme, parsed_url.netloc, parsed_url.path)
        if parsed_url.query:
            for query_parameter in parsed_url.query.split('&'):
                key, value = query_parameter.split('=')
                params[key] = value
        if params:
            url += '?%s' % urlencode(params, doseq=doseq)
        new_url = tc.go(url)
        return_code = tc.browser.get_code()
        assert return_code in allowed_codes, 'Invalid HTTP return code %s, allowed codes: %s' % \
            (return_code, ', '.join(str(code) for code in allowed_codes))
        return new_url

    def wait(self, **kwds):
        """Waits for the tools to finish"""
        return self.wait_for(lambda: self.get_running_datasets(), **kwds)

    def write_temp_file(self, content, suffix='.html'):
        fd, fname = tempfile.mkstemp(suffix=suffix, prefix='twilltestcase-')
        f = os.fdopen(fd, "w")
        f.write(content)
        f.close()
        return fname
