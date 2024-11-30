from galaxy.util import commands


def count_special_lines(word, filename, invert=False):
    """
    searching for special 'words' using the grep tool
    grep is used to speed up the searching and counting
    The number of hits is returned.
    """
    cmd = ["grep", "-c", "-E"]
    if invert:
        cmd.append('-v')
    cmd.extend([word, filename])
    try:
        out = commands.execute(cmd)
    except commands.CommandLineException:
        return 0
    return int(out)


def call_pysam_index(self, file_name, index_name, index_flag=None, stderr=None):
    """
    The pysam.index call can block the GIL, which can pause all threads, including
    the heartbeat thread. Therefore, start it as an external process.
    """
    if index_flag == '-b' or not index_flag:
        # IOError: No such file or directory: '-b' if index_flag is set to -b (pysam 0.15.4)
        cmd = ['python', '-c', f"import pysam; pysam.set_verbosity(0); pysam.index('{file_name}', '{index_name}')"]
    else:
        cmd = ['python', '-c',
               f"import pysam; pysam.set_verbosity(0); pysam.index('{index_flag}', '{file_name}', '{index_name}')"]
    if stderr:
        with open(stderr, 'w') as stderr:
            subprocess.check_call(cmd, stderr=stderr, shell=False)
    else:
        subprocess.check_call(cmd, shell=False)
