import functools
import os
import threading

from .custom_logging import get_logger


@functools.cache
def _get_docutils():
    """Return the docutils package, or None when it is not installed.

    Imported on demand rather than at module level because galaxy.util re-exports
    rst_to_html, so every importer of galaxy.util was loading docutils. Only tool
    help rendering needs it, and the per-job metadata and fetch processes never
    render help.
    """
    try:
        import docutils.core
        import docutils.io
        import docutils.utils
        import docutils.writers.html4css1

        return docutils
    except ImportError:
        return None


class FakeStream:
    def __init__(self, error):
        self.__error = error

    log_ = get_logger("docutils")

    def write(self, str):
        if len(str) > 0 and not str.isspace():
            if self.__error:
                raise Exception(str)
            self.log_.warning(str)


@functools.cache
def get_publisher(error=False):
    docutils = _get_docutils()
    assert docutils is not None, "docutils unavailable"
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


# Cached docutils publishers are stateful and not thread-safe.
_publish_lock = threading.Lock()


@functools.cache
def rst_to_html(s, error=False):
    if _get_docutils() is None:
        raise Exception("Attempted to use rst_to_html but docutils unavailable.")

    with _publish_lock:
        publisher = get_publisher(error=error)
        publisher.set_source(s, None)
        publisher.set_destination(None, None)
        return publisher.publish(enable_exit_status=False)
