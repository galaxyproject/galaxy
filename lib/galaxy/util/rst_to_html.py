import functools
import os

try:
    import docutils.core
    import docutils.io
    import docutils.utils
    import docutils.writers.html4css1
except ImportError:
    docutils = None  # type: ignore[assignment]

from .custom_logging import get_logger


class FakeStream:
    def __init__(self, error):
        self.__error = error

    log_ = get_logger("docutils")

    def write(self, str):
        if len(str) > 0 and not str.isspace():
            if self.__error:
                raise Exception(str)
            self.log_.warning(str)


@functools.lru_cache(maxsize=None)
def get_publisher(error=False):
    docutils_writer = docutils.writers.html4css1.Writer()
    docutils_template_path = os.path.join(os.path.dirname(__file__), "docutils_template.txt")
    no_report_level = docutils.utils.Reporter.SEVERE_LEVEL + 1
    settings_overrides = {
        "embed_stylesheet": False,
        "template": docutils_template_path,
        "warning_stream": FakeStream(error),
        "doctitle_xform": False,  # without option, very different rendering depending on
        # number of sections in help content.
        "halt_level": no_report_level,
        "output_encoding": "unicode",
    }

    if not error:
        # in normal operation we don't want noisy warnings, that's tool author business
        settings_overrides["report_level"] = no_report_level

    Publisher = docutils.core.Publisher
    pub = Publisher(
        parser=None,
        writer=docutils_writer,
        settings=None,
        source_class=docutils.io.StringInput,
        destination_class=docutils.io.StringOutput,
    )
    pub.set_components("standalone", "restructuredtext", "pseudoxml")
    pub.process_programmatic_settings(None, settings_overrides, None)
    return pub


@functools.lru_cache(maxsize=None)
def rst_to_html(s, error=False):
    if docutils is None:
        raise Exception("Attempted to use rst_to_html but docutils unavailable.")

    publisher = get_publisher(error=error)
    publisher.set_source(s, None)
    publisher.set_destination(None, None)
    return publisher.publish(enable_exit_status=False)
