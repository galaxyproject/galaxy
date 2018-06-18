import re
import traceback
from logging import getLogger

from galaxy.util.bunch import Bunch
from .error_level import StdioErrorLevel

log = getLogger(__name__)

DETECTED_JOB_STATE = Bunch(
    OK='ok',
    OUT_OF_MEMORY_ERROR='oom_error',
    GENERIC_ERROR='generic_error',
)


def check_output_regex(job, regex, stream, stream_append, max_error_level):
    """
    check a single regex against a stream

    regex the regex to check
    stream the stream to search in
    stream_append a list where the descriptions of the detected regexes can be appended
    max_error_level the maximum error level that has been detected so far
    returns the max of the error_level of the regex and the given max_error_level
    """
    regex_match = re.search(regex.match, stream, re.IGNORECASE)
    if regex_match:
        rexmsg = __regex_err_msg(regex_match, regex)
        log.info("Job %s: %s" % (job.get_id_tag(), rexmsg))
        stream_append.append(rexmsg)
        return max(max_error_level, regex.error_level)
    return max_error_level


def check_output_regex_byline(job, regex, stream, stream_append, max_error_level):
    """
    check a single regex against a stream line by line, since errors
    are expected to appear in the end of the stream we start with
    the last line
    returns the max of the error_level of the regex and the given max_error_level
    """
    for line in reversed(stream.split("\n")):
        regex_match = re.search(regex.match, line, re.IGNORECASE)
        if regex_match:
            rexmsg = __regex_err_msg(regex_match, regex)
            log.info("Job %s: %s" % (job.get_id_tag(), rexmsg))
            stream_append.append(rexmsg)
            return max(max_error_level, regex.error_level)
    return max_error_level


def check_output(tool, stdout, stderr, tool_exit_code, job):
    """
    Check the output of a tool - given the stdout, stderr, and the tool's
    exit code, return DETECTED_JOB_STATE.OK if the tool exited succesfully or
    error type otherwise. No exceptions should be thrown. If this code encounters
    an exception, it returns OK so that the workflow can continue;
    otherwise, a bug in this code could halt workflow progress.

    Note that, if the tool did not define any exit code handling or
    any stdio/stderr handling, then it reverts back to previous behavior:
    if stderr contains anything, then False is returned.
    """
    # By default, the tool succeeded. This covers the case where the code
    # has a bug but the tool was ok, and it lets a workflow continue.
    state = DETECTED_JOB_STATE.OK
    # messages (descriptions of the detected exit_code and regexes)
    # to be prepended to the stdout/stderr after all exit code and regex tests
    # are done (otherwise added messages are searched again).
    # messages are added it the order of detection
    stderr_toolmsg = []
    stdout_toolmsg = []
    try:
        # Check exit codes and match regular expressions against stdout and
        # stderr if this tool was configured to do so.
        # If there is a regular expression for scanning stdout/stderr,
        # then we assume that the tool writer overwrote the default
        # behavior of just setting an error if there is *anything* on
        # stderr.
        if len(tool.stdio_regexes) > 0 or len(tool.stdio_exit_codes) > 0:
            # Check the exit code ranges in the order in which
            # they were specified. Each exit_code is a StdioExitCode
            # that includes an applicable range. If the exit code was in
            # that range, then apply the error level and add a message.
            # If we've reached a fatal error rule, then stop.
            max_error_level = StdioErrorLevel.NO_ERROR
            if tool_exit_code is not None:
                for stdio_exit_code in tool.stdio_exit_codes:
                    if (tool_exit_code >= stdio_exit_code.range_start and
                            tool_exit_code <= stdio_exit_code.range_end):
                        # Tack on a generic description of the code
                        # plus a specific code description. For example,
                        # this might prepend "Job 42: Warning (Out of Memory)\n".
                        code_desc = stdio_exit_code.desc
                        if None is code_desc:
                            code_desc = ""
                        tool_msg = ("%s: Exit code %d (%s)" % (
                            StdioErrorLevel.desc(stdio_exit_code.error_level),
                            tool_exit_code,
                            code_desc))
                        log.info("Job %s: %s" % (job.get_id_tag(), tool_msg))
                        stderr_toolmsg.append(tool_msg)
                        max_error_level = max(max_error_level,
                                              stdio_exit_code.error_level)
                        if max_error_level >= StdioErrorLevel.MAX:
                            break

            if max_error_level < StdioErrorLevel.FATAL_OOM:
                # We'll examine every regex. Each regex specifies whether
                # it is to be run on stdout, stderr, or both. (It is
                # possible for neither stdout nor stderr to be scanned,
                # but those regexes won't be used.) We record the highest
                # error level, which are currently "warning" and "fatal".
                # If fatal, then we set the job's state to ERROR.
                # If warning, then we still set the job's state to OK
                # but include a message. We'll do this if we haven't seen
                # a fatal error yet
                for regex in tool.stdio_regexes:
                    # If ( this regex should be matched against stdout )
                    #   - Run the regex's match pattern against stdout
                    #   - If it matched, then determine the error level.
                    #       o If it was fatal, then we're done - break.
                    # Repeat the stdout stuff for stderr.
                    # TODO could test for stderr first? Reason: I would expect it to be smaller and contain the errors
                    if regex.stdout_match:
                        max_error_level = check_output_regex_byline(job, regex, stdout, stdout_toolmsg, max_error_level)
                        if max_error_level >= StdioErrorLevel.MAX:
                            break

                    if regex.stderr_match:
                        max_error_level = check_output_regex_byline(job, regex, stderr, stderr_toolmsg, max_error_level)
                        if max_error_level >= StdioErrorLevel.MAX:
                            break

            # If we encountered a fatal error, then we'll need to set the
            # job state accordingly. Otherwise the job is ok:
            if max_error_level == StdioErrorLevel.FATAL_OOM:
                state = DETECTED_JOB_STATE.OUT_OF_MEMORY_ERROR
            elif max_error_level >= StdioErrorLevel.FATAL:
                log.debug("Tool exit code indicates an error, failing job.")
                state = DETECTED_JOB_STATE.GENERIC_ERROR
            else:
                state = DETECTED_JOB_STATE.OK

        # When there are no regular expressions and no exit codes to check,
        # default to the previous behavior: when there's anything on stderr
        # the job has an error, and the job is ok otherwise.
        else:
            # TODO: Add in the tool and job id:
            # log.debug( "Tool did not define exit code or stdio handling; "
            #          + "checking stderr for success" )
            if stderr:
                peak = stderr[0:250]
                log.debug("Tool produced standard error failing job - [%s]" % peak)
                state = DETECTED_JOB_STATE.GENERIC_ERROR
            else:
                state = DETECTED_JOB_STATE.OK

    # On any exception, return True.
    except Exception:
        tb = traceback.format_exc()
        log.warning("Tool check encountered unexpected exception; " +
                    "assuming tool was successful: " + tb)
        state = DETECTED_JOB_STATE.OK

    # Store the modified stdout and stderr in the job:
    if len(stdout_toolmsg) > 0:
        stdout = "%s\n### END of messages added by Galaxy AND START of original stdout\n%s" % ("\n".join(stdout_toolmsg), stdout)
    if len(stderr_toolmsg) > 0:
        stderr = "%s\n### END of messages added by Galaxy AND START of original stderr\n%s" % ("\n".join(stderr_toolmsg), stderr)
    if job is not None:
        job.set_streams(stdout, stderr)

    return state


def __regex_err_msg(match, regex):
    """
    Return a message about the match on tool output using the given
    ToolStdioRegex regex object. The regex_match is a MatchObject
    that will contain the string matched on.
    """
    # Get the description for the error level:
    err_msg = StdioErrorLevel.desc(regex.error_level) + ": "
    # If there's a description for the regular expression, then use it.
    # Otherwise, we'll take the first 256 characters of the match.
    if None is not regex.desc:
        err_msg += regex.desc
    else:
        mstart = match.start()
        mend = match.end()
        err_msg += "Matched on "
        # TODO: Move the constant 256 somewhere else besides here.
        if mend - mstart > 256:
            err_msg += match.string[mstart : mstart + 256] + "..."
        else:
            err_msg += match.string[mstart: mend]
    return err_msg
