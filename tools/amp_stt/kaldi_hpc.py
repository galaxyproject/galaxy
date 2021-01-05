#!/bin/env python3
"""
This will run the Fraunhofer-supplied GPU-enabled Kaldi Singularity container
on the Carbonate HPC resource at IU and retrieve the results.
"""
import argparse
import paramiko
import getpass
from pathlib import Path
import logging
import sys
import os
import socket
import time
import stat
import configparser
import tempfile


logging.basicConfig(level=logging.DEBUG, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger()

def main():
    """
    Run the kaldi singularity container on carbonate and retrieve the results
    """
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("--quiet", default=False, action="store_true", help="Turn off output")
    parser.add_argument("--nocleanup", default=False, action="store_true", help="Don't clean up the remote directories")
    parser.add_argument("--email", default=None, type=str, help="Email address for status reports")
    parser.add_argument("--memory", default=32, type=int, help="Memory allocation request in GB")
    parser.add_argument("config", help="Configuration file")
    parser.add_argument("input", help="input audio file")
    parser.add_argument("kaldi_transcript_json", help="Kaldi JSON output")
    parser.add_argument("kaldi_transcript_txt", help="Kalid TXT output")
    parser.add_argument("amp_transcript_json", help="AMP JSON output")
    args = parser.parse_args()

    # set up logging
    if args.debug:
        logger.setLevel(logging.DEBUG)  
    else:
        logger.setLevel(logging.INFO)

    if args.quiet:
        logger.setLevel(logging.ERROR)

    # read the configuration file
    config = configparser.ConfigParser()
    config.read(args.config)

    # make the ssh connection and get moving
    error = False
    with paramiko.SSHClient() as ssh:
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=config['remote']['host'], 
                    port=config['remote']['port'], 
                    username=config['auth']['user'],
                    key_filename=config['auth']['key_file'],
                    passphrase=config['auth']['passphrase'])
        sftp = ssh.open_sftp()

        # go to the workspace directory
        try:
            sftp.chdir(config['remote']['workspace'])
        except Exception as e:
            logger.critical(f"Cannot change to base directory {config['remote']['workspace']}: {e}")
            exit(1)

        try:
            # create the working directory for the remote process    
            workdir = f"{socket.gethostname().split('.')[0]}-{os.getpid()}-{time.time()}"
            workspace = config['remote']['workspace'] + "/" + workdir
            logger.info(f"Creating work directory: {workdir}")
            sftp.mkdir(workdir)
            sftp.chdir(workdir)
            for d in ('in_dir', 'out_dir', 'work_dir'):
                sftp.mkdir(d)
        
            # copy the input file to the remote
            ifile = Path(args.input)
            ofile = f"in_dir/{ifile.name}"
            logging.info(f"Pushing {args.input} to {ofile}")
            sftp.put(ifile, ofile)

            # while we're here, build a dict that holds the remote
            # output names and the corresponding local output filenames
            out_map = {f'out_dir/{ifile.stem}.amp.json': args.amp_transcript_json,
                       f'out_dir/{ifile.stem}.pua.json': args.kaldi_transcript_json,
                       f'out_dir/{ifile.stem}.txt': args.kaldi_transcript_txt}

            
            # Build a job file which we will be submitting to the queing system.
            # This job reproduces the behavior of the Fraunhofer-supplied run.sh
            # because this way the cleanup is easier and there is a smaller chance
            # of failure.
            with tempfile.TemporaryDirectory() as td:
                jobfile = Path(td, 'job.sh')
                with open(jobfile, "w") as f:
                    f.write("#!/bin/bash\n")
                    f.write(f"#SBATCH -p {config['job']['partition']}\n")
                    f.write(f"#SBATCH --gres {config['job']['gres']}\n")
                    f.write(f"#SBATCH -o {workspace}/stdout.txt\n")
                    f.write(f"#SBATCH -e {workspace}/stderr.txt\n")
                    if args.email is not None:
                        f.write("#SBATCH --mail-type=ALL\n")
                        f.write(f"#SBATCH --mail-user={args.email}\n")
                    f.write(f"#SBATCH --mem={args.memory}G\n")
                    f.write("module load singularity\n")
                    f.write(f"singularity run --nv \\\n")
                    f.write(f"  --bind {workspace}/in_dir:/amp_files/input \\\n")
                    f.write(f"  --bind {workspace}/out_dir:/amp_files/output \\\n")
                    f.write(f"  --bind {workspace}/work_dir:/amp_files/data \\\n")
                    f.write(f"  {config['remote']['kaldi_sif']} \\\n")
                    f.write(f"     /opt/amp/ampservice/main.py \\\n")
                    f.write(f'     -i /amp_files/input \\\n')
                    f.write(f"     -o /amp_files/output \\\n")
                    f.write(f"     -d /amp_files/data \\\n")
                    f.write(f"     --log-level debug --single-run --lowercase\n")
                    f.write(f"echo $? > {workspace}/finished.out\n")
                sftp.put(jobfile, "job.sh")
                sftp.chmod("job.sh", 0o755)

            # now that the job exists on carbonate, queue it
            command = f"cd {workspace}; sbatch {workspace}/job.sh; echo $?"
            logger.info(f"Running: {command}")
            _, stdout, stderr = ssh.exec_command(command)
            stdout = stdout.readlines()
            rc = int(stdout[-1])
            logger.info(f"Return code: {rc}")
            logger.debug(f"STDOUT: {''.join(stdout)}")
            logger.debug(f"STDERR: {''.join(stderr.readlines())}")

            if rc != 0:
                raise Exception(f"Cannot queue job RC={rc}")

            # the job is queued, so we just need to wait for the finished.out
            # file to appear (which contains the return code)
            poll = 30
            logger.info(f"Checking every {poll}s for {workspace}/finished.out to appear")
            while True:
                try:
                    sftp.stat(f"{workspace}/finished.out")
                    logging.info(f"{workspace}/finished.out has appeared")
                    break
                except FileNotFoundError as e:
                    # we're expecting this.
                    logging.debug(f"Still waiting.")
                    time.sleep(poll)

            with tempfile.TemporaryDirectory() as td:
                logging.debug("Retrieving finished.out")
                sftp.get(f"{workspace}/finished.out", f"{td}/finished.out")
                with open(f"{td}/finished.out") as f:
                    rc = int(f.readline())
                if rc != 0:
                    # uh oh.  Grab the stdout and stderr bits and dump them.
                    logging.error(f"Not-zero return code from batch job: {rc}")
                    for out in ("stdout.txt", "stderr.txt"):
                        try:
                            sftp.get(f"{workspace}/{out}", f"{td}/{out}")
                            with open(f"{td}/{out}") as f:
                                output = f.read()
                            logging.error(f"Contents of {out}:\n{output}")
                        except Exception as e:
                            pass
                    error = True
                else:
                    for o in out_map:
                        logging.info(f"Retrieving {o} as {out_map[o]}")
                        sftp.get(f"{workspace}/{o}", out_map[o])
                        
        except Exception as e:
            logger.critical(f"Error during processing: {e}")
            error = True
        finally:
            if args.nocleanup:
                logger.info(f"Not cleaning up remote directory {workspace}")
            else:
                logger.info(f"Cleaning up work directory {workspace}")
                sftp.chdir("..")
                clean_up(sftp, workdir)

    exit(1 if error else rc)


def clean_up(sftp, dir):
    entries = list(sftp.listdir_iter(dir))
    for f in entries:
        if f.st_mode & stat.S_IFDIR:
            clean_up(sftp, f"{dir}/{f.filename}")
        else:
            logger.debug(f"Removing {dir}/{f.filename}")
            sftp.remove(f"{dir}/{f.filename}")
    logger.debug(f"Removing directory {dir}")
    sftp.rmdir(dir)

if __name__ == "__main__":
    main()