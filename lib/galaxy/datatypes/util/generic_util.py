from galaxy.util import commands


def count_special_lines(word, filename, invert=False):
    """
    searching for special 'words' using the grep tool
    grep is used to speed up the searching and counting
    The number of hits is returned.
    """
    cmd = ["grep", "-c", "-E"]
    if invert:
        cmd.append("-v")
    cmd.extend([word, filename])
    try:
        out = commands.execute(cmd)
    except commands.CommandLineException:
        return 0
    return int(out)
