import subprocess


def count_special_lines( word, filename, invert=False ):
    """
        searching for special 'words' using the grep tool
        grep is used to speed up the searching and counting
        The number of hits is returned.
    """
    try:
        cmd = ["grep", "-c", "-E"]
        if invert:
            cmd.append('-v')
        cmd.extend([word, filename])
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        return int(out.communicate()[0].split()[0])
    except:
        pass
    return 0
