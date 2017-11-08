if [ -n "$SLURM_JOB_ID" ]; then
    GALAXY_MEMORY_MB=`scontrol -do show job "$SLURM_JOB_ID" | sed 's/.*\( \|^\)Mem=\([0-9][0-9]*\)\( \|$\).*/\2/p;d'`
fi
[ "$GALAXY_MEMORY_MB" -gt 0 ] >/dev/null && export GALAXY_MEMORY_MB || unset GALAXY_MEMORY_MB
