import re
from enum import Enum
from logging import getLogger

from galaxy.tool_util.parser.stdio import StdioErrorLevel
from galaxy.util import unicodify

log = getLogger(__name__)


class DETECTED_JOB_STATE(str, Enum):
    OK = "ok"
    OUT_OF_MEMORY_ERROR = "oom_error"
    GENERIC_ERROR = "generic_error"


ERROR_PEEK_SIZE = 2000


def check_output_regex(job_id_tag, regex, stream, stream_name, job_messages, max_error_level):
    """
    check a single regex against a stream

    regex the regex to check
    stream the stream to search in
    job_messages a list where the descriptions of the detected regexes can be appended
    max_error_level the maximum error level that has been detected so far
    returns the max of the error_level of the regex and the given max_error_level
    """
    regex_match = re.search(regex.match, stream, re.IGNORECASE)
    if regex_match:
        reason = __regex_err_msg(regex_match, stream_name, regex)
        job_messages.append(reason)
        return max(max_error_level, regex.error_level)
    return max_error_level


def check_output(stdio_regexes, stdio_exit_codes, stdout, stderr, tool_exit_code, job_id_tag):
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

    stdout = unicodify(stdout, strip_null=True)
    stderr = unicodify(stderr, strip_null=True)

    # messages (descriptions of the detected exit_code and regexes)
    # to be prepended to the stdout/stderr after all exit code and regex tests
    # are done (otherwise added messages are searched again).
    # messages are added it the order of detection

    # If job is failed, track why.
    job_messages = []

    try:
        # Check exit codes and match regular expressions against stdout and
        # stderr if this tool was configured to do so.
        # If there is a regular expression for scanning stdout/stderr,
        # then we assume that the tool writer overwrote the default
        # behavior of just setting an error if there is *anything* on
        # stderr.
        if len(stdio_regexes) > 0 or len(stdio_exit_codes) > 0:
            # Check the exit code ranges in the order in which
            # they were specified. Each exit_code is a StdioExitCode
            # that includes an applicable range. If the exit code was in
            # that range, then apply the error level and add a message.
            # If we've reached a fatal error rule, then stop.
            max_error_level = StdioErrorLevel.NO_ERROR
            if tool_exit_code is not None:
                for stdio_exit_code in stdio_exit_codes:
                    if tool_exit_code >= stdio_exit_code.range_start and tool_exit_code <= stdio_exit_code.range_end:
                        # Tack on a generic description of the code
                        # plus a specific code description. For example,
                        # this might prepend "Job 42: Warning (Out of Memory)\n".
                        code_desc = stdio_exit_code.desc
                        if None is code_desc:
                            code_desc = ""
                        desc = "%s: Exit code %d (%s)" % (
                            StdioErrorLevel.desc(stdio_exit_code.error_level),
                            tool_exit_code,
                            code_desc,
                        )
                        reason = {
                            "type": "exit_code",
                            "desc": desc,
                            "exit_code": tool_exit_code,
                            "code_desc": code_desc,
                            "error_level": stdio_exit_code.error_level,
                        }
                        job_messages.append(reason)
                        max_error_level = max(max_error_level, stdio_exit_code.error_level)
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
                for regex in stdio_regexes:
                    # If ( this regex should be matched against stdout )
                    #   - Run the regex's match pattern against stdout
                    #   - If it matched, then determine the error level.
                    #       o If it was fatal, then we're done - break.
                    if regex.stderr_match:
                        max_error_level = check_output_regex(
                            job_id_tag, regex, stderr, "stderr", job_messages, max_error_level
                        )
                        if max_error_level >= StdioErrorLevel.MAX:
                            break

                    if regex.stdout_match:
                        max_error_level = check_output_regex(
                            job_id_tag, regex, stdout, "stdout", job_messages, max_error_level
                        )
                        if max_error_level >= StdioErrorLevel.MAX:
                            break

            # If we encountered a fatal error, then we'll need to set the
            # job state accordingly. Otherwise the job is ok:
            if max_error_level == StdioErrorLevel.FATAL_OOM:
                state = DETECTED_JOB_STATE.OUT_OF_MEMORY_ERROR
            elif max_error_level >= StdioErrorLevel.FATAL:
                reason = ""
                if job_messages:
                    reason = f" Reasons are {job_messages}"
                log.info(f"Job error detected, failing job.{reason}")
                state = DETECTED_JOB_STATE.GENERIC_ERROR

        # When there are no regular expressions and no exit codes to check,
        # default to the previous behavior: when there's anything on stderr
        # the job has an error, and the job is ok otherwise.
        else:
            # TODO: Add in the tool and job id:
            # log.debug( "Tool did not define exit code or stdio handling; "
            #          + "checking stderr for success" )
            if stderr:
                state = DETECTED_JOB_STATE.GENERIC_ERROR
                peek = stderr[0:ERROR_PEEK_SIZE] if stderr else ""
                log.info(f"Job failed because of contents in the standard error stream: [{peek}]")
    except Exception:
        log.exception("Job state check encountered unexpected exception; assuming execution successful")

    return state, stdout, stderr, job_messages


def __regex_err_msg(match, stream, regex):
    """
    Return a message about the match on tool output using the given
    ToolStdioRegex regex object. The regex_match is a MatchObject
    that will contain the string matched on.
    """
    # Get the description for the error level:
    desc = f"{StdioErrorLevel.desc(regex.error_level)}: "
    mstart = match.start()
    mend = match.end()
    if mend - mstart > 256:
        match_str = f"{match.string[mstart:mstart + 256]}..."
    else:
        match_str = match.string[mstart:mend]

    # If there's a description for the regular expression, then use it.
    # Otherwise, we'll take the first 256 characters of the match.
    if regex.desc is not None:
        desc += regex.desc
    else:
        desc += f"Matched on {match_str}"
    return {
        "type": "regex",
        "stream": stream,
        "desc": desc,
        "code_desc": regex.desc,
        "match": match_str,
        "error_level": regex.error_level,
    }
