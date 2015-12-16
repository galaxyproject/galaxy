export GALAXY_SLOTS_CONFIGURED="1"
if [ -n "$SLURM_NTASKS" ] || [ -n "$SLURM_CPUS_PER_TASK" ]; then
    # Multiply these values since SLURM_NTASKS is total tasks over all nodes.
    # GALAXY_SLOTS maps to CPUS on a single node and shouldn't be used for
    # multi-node requests.
    GALAXY_SLOTS=`expr "${SLURM_NTASKS:-1}" \* "${SLURM_CPUS_PER_TASK:-1}"`
elif [ -n "$NSLOTS" ]; then
    GALAXY_SLOTS="$NSLOTS"
elif [ -n "$PBS_NCPUS" ]; then
    GALAXY_SLOTS="$PBS_NCPUS"
elif [ -f "$PBS_NODEFILE" ]; then
    GALAXY_SLOTS=`wc -l < $PBS_NODEFILE`
elif [ -n "$LSB_DJOB_NUMPROC" ]; then
    GALAXY_SLOTS="$LSB_DJOB_NUMPROC"
else
    GALAXY_SLOTS="1"
    unset GALAXY_SLOTS_CONFIGURED
fi
