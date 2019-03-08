"""Binary classes"""
from __future__ import print_function

import logging

from text import Html
from galaxy.web import url_for


log = logging.getLogger(__name__)


class Realtime(Html):
    """Class describing a RealtimeTool Default output file"""
    file_ext = "realtimetool"
    composite_type = 'auto_primary_file'

    def set_peek(self, dataset, is_multi_byte=False):
        dataset.blurb = "RealtimeTool"
        dataset.peek = 'Finished RealTimeTool'


    def display_peek(self, dataset):
        try:
            if not dataset.peek:
                self.set_peek(dataset)
            return dataset.peek
        except Exception:
            return "Realtime Tool file"

    def generate_primary_file(self, dataset=None):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        defined_files = self.get_composite_files(dataset=dataset).items()
        rval = ["<html><head><title>Files for Composite Dataset (%s)</title></head>" % (self.file_ext)]
        if defined_files:
            rval.append("<p/>This composite dataset is composed of the following defined files:<p/><ul>")
            for composite_name, composite_file in defined_files:
                opt_text = ''
                if composite_file.optional:
                    opt_text = ' (optional)'
                missing_text = ''
                if not os.path.exists(os.path.join(dataset.extra_files_path, composite_name)):
                    missing_text = ' (missing)'
                rval.append('<li><a href="%s">%s</a>%s%s</li>' % (composite_name, composite_name, opt_text, missing_text))
            rval.append("</ul>")
        defined_files = map(lambda x: x[0], defined_files)
        extra_files = []
        for (dirpath, dirnames, filenames) in os.walk(dataset.extra_files_path, followlinks=True):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(dirpath, filename), dataset.extra_files_path)
                if rel_path not in defined_files:
                    extra_files.append(rel_path)
        if extra_files:
            rval.append("<p/>This composite dataset contains these undefined files:<p/><ul>")
            for rel_path in extra_files:
                rval.append('<li><a href="%s">%s</a></li>' % (rel_path, rel_path))
            rval.append('</ul>')
        if not (defined_files or extra_files):
            rval.append("<p/>This composite dataset does not contain any files!<p/><ul>")
        rval.append('</html>')
        return "\n".join(rval)

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, offset=None, ck_size=None, **kwd):
        log.debug('dataset.realtime_tool.id %s', dataset.realtime_tool.id)
        rtt = dataset.realtime_tool
        if rtt and rtt.active:
            return trans.response.send_redirect(url_for(controller='realtime', action='index', realtime_id=trans.security.encode_id(rtt.id)))
        return super(Realtime, self).display_data(trans, dataset, preview=preview, filename=filename, to_ext=to_ext, offset=offset, ck_size=ck_size, **kwd)


if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules[__name__])
