import os, logging
log = logging.getLogger( __name__ )

def _file_len(fname):
    i = 0
    f = open(fname)
    for i, l in enumerate(f):
        pass
    f.close()
    return i + 1

def _fq_seq_count(fname):
    count = 0
    f = open(fname)
    for i, l in enumerate(f):
        if l.startswith('@'):
            count += 1
    f.close()
    return count

def split_fq(input_file, working_directory, parts):
    # Temporary, switch this to use the fq reader in lib/galaxy_utils/sequence.
    outputs = []
    length = _fq_seq_count(input_file)
    if length < 1:
        return outputs
    if length < parts:
        parts = length
    len_each, remainder = divmod(length, parts)
    f = open(input_file, 'rt')
    for p in range(0, parts):
        part_dir = os.path.join( os.path.abspath(working_directory), 'task_%s' % p)
        if not os.path.exists( part_dir ):
            os.mkdir( part_dir )
        part_path = os.path.join(part_dir, os.path.basename(input_file))
        part_file = open(part_path, 'w')
        for l in range(0, len_each):
            part_file.write(f.readline())
            part_file.write(f.readline())
            part_file.write(f.readline())
            part_file.write(f.readline())
        if remainder > 0:
            part_file.write(f.readline())
            part_file.write(f.readline())
            part_file.write(f.readline())
            part_file.write(f.readline())
            remainder -= 1
        outputs.append(part_path)
        part_file.close()
    f.close()
    return outputs

def split_txt(input_file, working_directory, parts):
    outputs = []
    length = _file_len(input_file)
    if length < parts:
        parts = length
    len_each, remainder = divmod(length, parts)
    f = open(input_file, 'rt')
    for p in range(0, parts):
        part_dir = os.path.join( os.path.abspath(working_directory), 'task_%s' % p)
        if not os.path.exists( part_dir ):
            os.mkdir( part_dir )
        part_path = os.path.join(part_dir, os.path.basename(input_file))
        part_file = open(part_path, 'w')
        for l in range(0, len_each):
            part_file.write(f.readline())
        if remainder > 0:
            part_file.write(f.readline())
            remainder -= 1
        outputs.append(part_path)
        part_file.close()
    f.close()
    return outputs
    
def split( input_file, working_directory, parts, file_type = None):
    #Implement a better method for determining how to split.
    if file_type.startswith('fastq'):
        return split_fq(input_file, working_directory, parts)
    else:
        return split_txt(input_file, working_directory, parts)
    
def merge( working_directory, output_file ):
    output_file_name = os.path.basename(output_file)
    task_dirs = [os.path.join(working_directory, x) for x in os.listdir(working_directory) if x.startswith('task_')]
    task_dirs.sort(key = lambda x: int(x.split('task_')[-1]))
    for task_dir in task_dirs:
        try:
            os.system( 'cat %s >> %s' % ( os.path.join(task_dir, output_file_name), output_file ) )
        except Exception, e:
            log.error(str(e))
