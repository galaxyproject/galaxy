# -*- coding:utf-8 -*-
from mako import runtime, filters, cache

UNDEFINED = runtime.UNDEFINED
STOP_RENDERING = runtime.STOP_RENDERING
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 10
_modified_time = 1490897004.899657
_enable_loop = True
_template_filename = 'htdocs/login.mako'
_template_uri = 'login.mako'
_source_encoding = 'utf-8'
_exports = ['add_js']


def _mako_get_namespace(context, name):
    try:
        return context.namespaces[(__name__, name)]
    except KeyError:
        _mako_generate_namespaces(context)
        return context.namespaces[(__name__, name)]


def _mako_generate_namespaces(context):
    pass


def _mako_inherit(template, context):
    _mako_generate_namespaces(context)
    return runtime._inherit_from(context, u'root.mako', _template_uri)


def render_body(context, **pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        submit_text = context.get('submit_text', UNDEFINED)
        acr = context.get('acr', UNDEFINED)
        title = context.get('title', UNDEFINED)
        login_title = context.get('login_title', UNDEFINED)
        passwd_title = context.get('passwd_title', UNDEFINED)
        tos_uri = context.get('tos_uri', UNDEFINED)
        policy_uri = context.get('policy_uri', UNDEFINED)
        action = context.get('action', UNDEFINED)
        query = context.get('query', UNDEFINED)
        login = context.get('login', UNDEFINED)
        password = context.get('password', UNDEFINED)
        logo_uri = context.get('logo_uri', UNDEFINED)
        __M_writer = context.writer()
        __M_writer(u'\n<div class="header">\n    <h1><a href="/">')
        __M_writer(unicode(title))
        __M_writer(u'</a></h1>\n</div>\n<div class="login_form" class="block">\n    <form action="')
        __M_writer(unicode(action))
        __M_writer(u'" method="post" class="login form">\n        <input type="hidden" name="query" value="')
        __M_writer(unicode(query))
        __M_writer(u'"/>\n        <input type="hidden" name="acr_values" value="')
        __M_writer(unicode(acr))
        __M_writer(u'"/>\n        <table>\n            <tr>\n                <td>')
        __M_writer(unicode(login_title))
        __M_writer(u'</td>\n                <td><input type="text" name="login" value="')
        __M_writer(unicode(login))
        __M_writer(u'"/></td>\n            </tr>\n            <tr>\n                <td>')
        __M_writer(unicode(passwd_title))
        __M_writer(u'</td>\n                <td><input type="password" name="password"\n                value="')
        __M_writer(unicode(password))
        __M_writer(
            u'"/></td>\n            </tr>\n            <tr>\n                </td>\n                <td><input type="submit" name="form.commit"\n                        value="')
        __M_writer(unicode(submit_text))
        __M_writer(u'"/></td>\n            </tr>\n        </table>\n    </form>\n')
        if logo_uri:
            __M_writer(u'        <img src="')
            __M_writer(unicode(logo_uri))
            __M_writer(u'" alt="Client logo">\n')
        if policy_uri:
            __M_writer(u'        <a href="')
            __M_writer(unicode(policy_uri))
            __M_writer(u'"><strong>Client&#39;s Policy</strong></a>\n')
        if tos_uri:
            __M_writer(u'        <a href="')
            __M_writer(unicode(tos_uri))
            __M_writer(u'"><strong>Client&#39;s Terms of Service</strong></a>\n')
        __M_writer(u'</div>\n\n')
        __M_writer(u'\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_add_js(context):
    __M_caller = context.caller_stack._push_frame()
    try:
        __M_writer = context.writer()
        __M_writer(
            u'\n    <script type="text/javascript">\n        $(document).ready(function() {\n            bookie.login.init();\n        });\n    </script>\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


"""
__M_BEGIN_METADATA
{"source_encoding": "utf-8", "line_map": {"27": 0, "44": 1, "45": 3, "46": 3, "47": 6, "48": 6, "49": 7, "50": 7, "51": 8, "52": 8, "53": 11, "54": 11, "55": 12, "56": 12, "57": 15, "58": 15, "59": 17, "60": 17, "61": 22, "62": 22, "63": 26, "64": 27, "65": 27, "66": 27, "67": 29, "68": 30, "69": 30, "70": 30, "71": 32, "72": 33, "73": 33, "74": 33, "75": 35, "76": 43, "82": 37, "86": 37, "92": 86}, "uri": "login.mako", "filename": "htdocs/login.mako"}
__M_END_METADATA
"""
