# -*- coding:utf-8 -*-
from mako import runtime, filters, cache

UNDEFINED = runtime.UNDEFINED
STOP_RENDERING = runtime.STOP_RENDERING
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 10
_modified_time = 1490897004.910343
_enable_loop = True
_template_filename = u'Templates/root.mako'
_template_uri = u'root.mako'
_source_encoding = 'utf-8'
_exports = ['css_link', 'pre', 'post', 'css']


def render_body(context, **pageargs):
    __M_caller = context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)

        def pre():
            return render_pre(context._locals(__M_locals))

        self = context.get('self', UNDEFINED)
        set = context.get('set', UNDEFINED)

        def post():
            return render_post(context._locals(__M_locals))

        next = context.get('next', UNDEFINED)
        __M_writer = context.writer()
        self.seen_css = set()

        __M_writer(u'\n')
        __M_writer(u'\n')
        __M_writer(u'\n')
        __M_writer(u'\n')
        __M_writer(u'\n')
        __M_writer(u'<html>\n<head><title>OpenID Connect provider example</title>\n')
        __M_writer(unicode(self.css()))
        __M_writer(u'\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n</head>\n<body>\n')
        __M_writer(unicode(pre()))
        __M_writer(u'\n')
        __M_writer(unicode(next.body()))
        __M_writer(u'\n')
        __M_writer(unicode(post()))
        __M_writer(u'\n</body>\n</html>\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


def render_css_link(context, path, media=''):
    __M_caller = context.caller_stack._push_frame()
    try:
        context._push_buffer()
        self = context.get('self', UNDEFINED)
        __M_writer = context.writer()
        __M_writer(u'\n')
        if path not in self.seen_css:
            __M_writer(u'    <link rel="stylesheet" type="text/css" href="')
            __M_writer(filters.html_escape(unicode(path)))
            __M_writer(u'" media="')
            __M_writer(unicode(media))
            __M_writer(u'">\n')
        __M_writer(u'    ')
        self.seen_css.add(path)

        __M_writer(u'\n')
    finally:
        __M_buf, __M_writer = context._pop_buffer_and_writer()
        context.caller_stack._pop_frame()
    __M_writer(filters.trim(__M_buf.getvalue()))
    return ''


def render_pre(context):
    __M_caller = context.caller_stack._push_frame()
    try:
        context._push_buffer()
        __M_writer = context.writer()
        __M_writer(u'\n')
    finally:
        __M_buf, __M_writer = context._pop_buffer_and_writer()
        context.caller_stack._pop_frame()
    __M_writer(filters.trim(__M_buf.getvalue()))
    return ''


def render_post(context):
    __M_caller = context.caller_stack._push_frame()
    try:
        context._push_buffer()
        __M_writer = context.writer()
        __M_writer(
            u'\n<div>\n    <div class="footer">\n        <p>&#169; Copyright 2014 Ume&#229; Universitet &nbsp;</p>\n    </div>\n</div>\n')
    finally:
        __M_buf, __M_writer = context._pop_buffer_and_writer()
        context.caller_stack._pop_frame()
    __M_writer(filters.trim(__M_buf.getvalue()))
    return ''


def render_css(context):
    __M_caller = context.caller_stack._push_frame()
    try:
        context._push_buffer()

        def css_link(path, media=''):
            return render_css_link(context, path, media)

        __M_writer = context.writer()
        __M_writer(u'\n    ')
        __M_writer(unicode(css_link('/css/main.css', 'screen')))
        __M_writer(u'\n')
    finally:
        __M_buf, __M_writer = context._pop_buffer_and_writer()
        context.caller_stack._pop_frame()
    __M_writer(filters.trim(__M_buf.getvalue()))
    return ''


"""
__M_BEGIN_METADATA
{"source_encoding": "utf-8", "line_map": {"16": 0, "28": 1, "30": 1, "31": 7, "32": 10, "33": 12, "34": 19, "35": 22, "36": 24, "37": 24, "38": 28, "39": 28, "40": 31, "41": 31, "42": 32, "43": 32, "49": 2, "55": 2, "56": 3, "57": 4, "58": 4, "59": 4, "60": 4, "61": 4, "62": 6, "63": 6, "65": 6, "73": 11, "78": 11, "86": 13, "91": 13, "99": 8, "106": 8, "107": 9, "108": 9, "116": 108}, "uri": "root.mako", "filename": "Templates/root.mako"}
__M_END_METADATA
"""
