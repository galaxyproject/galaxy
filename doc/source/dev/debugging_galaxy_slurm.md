
# Debugging Galaxy: Slurm Compute Cluster

This document explains how to debug a Galaxy instance that uses a Slurm compute cluster (not the
default LocalRunner). If you have a MacOS machine, you need to create a Linux VM using Oracle's
VirtualBoxVM and run the instructions in the VM. For reference, I created a 64-bit Linux VM with
4096 MB of RAM and 32 GB of disk space (all other parameters were left as default) and managed to
successfully run the instructions. If using a Linux VM, you may need to install Git, Python, VSCode,
and Docker (if using Irods storage). Finally, These instructions are intended for developers who
want to debug their Galaxy instance and are not meant for deployment purposes (We have nice Ansible
playbooks for that).

## Debugging Galaxy in VS Code

1. Install libslurm-dev
    * `sudo apt install libslurm-dev`
    * On my VM, the above command puts slurm/slurm.h in /usr/include and libslurm.a in /usr/lib/x86_64-linux-gnu
    * You need these header and library files to compile slurm-drmaa in the next step

2. Install slurm-drmaa
    * Download slurm-drmaa tar file from https://github.com/natefoo/slurm-drmaa/releases/download/1.1.2/slurm-drmaa-1.1.2.tar.gz
    * Extract the downloaded tar file into home directory: `tar -xzvf slurm-drmaa-1.1.2.tar.gz -C ~`
    * To compile and install slurm-drmaa
        * `cd ~/slurm-drmaa-1.1.2`
        * `./configure --with-slurm-inc=/usr/include --with-slurm-lib=/usr/lib/x86_64-linux-gpu`
        * `sudo make install`
        * On my VM, the above command puts libdrmaa.so in /usr/local/lib. You need the path to this file in the next step

3. Replace the contents of ~/galaxy/config/job_conf.xml with the following code snippet (create the file if it does not already exist)
    ```
    <?xml version="1.0"?>
    <job_conf>
        <plugins workers="3">
            <plugin id="slurm" type="runner" load="galaxy.jobs.runners.slurm:SlurmJobRunner">
                <param id="drmaa_library_path">/usr/local/lib/libdrmaa.so</param>
            </plugin>
        </plugins>
        <destinations default="slurm">
            <destination id="slurm" runner="slurm"/>
        </destinations>
    </job_conf>
    ```

4. Uncomment the following line in ~/galaxy/config/galaxy.yml (If the file does not exist, create it by copying ~/galaxy/config/galaxy.yml.sample)
    * `job_config_file: job_conf.xml`

5. Install Slurm (Instructions borrowed from https://gist.github.com/ckandoth/2acef6310041244a690e4c08d2610423)
    * Install the necessary packages: `sudo apt install -y slurm-wlm slurm-wlm-doc`
    * Load /usr/share/doc/slurm-wlm/html/configurator.html in a browser
        * Set your VM's hostname in `SlurmctldHost` and `NodeName`
        * Set `StateSaveLocation` to `/var/spool/slurmctld`
        * Set `SlurmdSpoolDir` to `/var/spool/slurmd`
        * Set `ProctrackType` to `LinuxProc`
        * Set `SelectType` to `Cons_res`
        * Set `SelectTypeParameters` to `CR_Core_Memory`
        * Set `JobAcctGatherType` to `Linux`
        * Hit Submit and save the resulting text into `/etc/slurm-llnl/slurm.conf`
            * I.e., the configuration file referred to in /lib/systemd/system/slurmctld.service and /lib/systemd/system/slurmd.service
    * Create /var/spool/slurmd and /var/spool/slurmctld directories and /var/log/slurm_jobacct.log file and set ownership appropriately
        * `sudo mkdir -p /var/spool/slurmd`
        * `sudo mkdir -p /var/spool/slurmctld`
        * `sudo touch /var/log/slurm_jobacct.log`
        * `sudo chown slurm:slurm /var/spool/slurmd /var/spool/slurmctld /var/log/slurm_jobacct.log`
    * Install mailutils so that Slurm won't complain about /bin/mail missing
        * `sudo apt install -y mailutils`
    * Make sure munge is installed/running, and a munge.key was created with user-only read-only permissions, owned by munge:munge
        * `sudo apt install munge`
        * `sudo service munge start`
        * `sudo ls -l /etc/munge/munge.key`
    * Start slurmd and slurmctld services
        * `sudo service slurmd start`
        * `sudo service slurmctld start`

6. Follow the instructions [here](debugging_galaxy) to setup VSCode for debugging.

Enjoy debugging session your Galaxy instance backed by a Slurm cluster!
