if [ -n "$SLURM_JOB_ID" ]; then
    GALAXY_MEMORY_MB=`scontrol -do show job "$SLURM_JOB_ID" | sed 's/.*\( \|^\)Mem=\([0-9][0-9]*\)\( \|$\).*/\2/p;d'` 2>memory_statement.log
fi
[ "${GALAXY_MEMORY_MB--1}" -gt 0 ] 2>>memory_statement.log && export GALAXY_MEMORY_MB || unset GALAXY_MEMORY_MB
