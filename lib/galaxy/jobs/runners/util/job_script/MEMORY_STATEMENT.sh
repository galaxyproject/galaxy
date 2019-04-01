if [ -n "$SLURM_JOB_ID" ]; then
    GALAXY_MEMORY_MB=`scontrol -do show job "$SLURM_JOB_ID" | sed 's/.*\( \|^\)Mem=\([0-9][0-9]*\)\( \|$\).*/\2/p;d'` 2>memory_statement.log
fi
if [ -n "$SGE_HGR_h_vmem" ]; then
    GALAXY_MEMORY_MB_PER_SLOT=`echo "$SGE_HGR_h_vmem" | sed 's/G$/ * 1024/' | bc | cut -d"." -f1` 2>memory_statement.log
fi

if [ -z "$GALAXY_MEMORY_MB_PER_SLOT" -a -n "$GALAXY_MEMORY_MB" ]; then
    GALAXY_MEMORY_MB_PER_SLOT=$(($GALAXY_MEMORY_MB / $GALAXY_SLOTS))
elif [ -z "$GALAXY_MEMORY_MB" -a -n "$GALAXY_MEMORY_MB_PER_SLOT" ]; then
    GALAXY_MEMORY_MB=$(($GALAXY_MEMORY_MB_PER_SLOT * $GALAXY_SLOTS))
fi
[ "${GALAXY_MEMORY_MB--1}" -gt 0 ] 2>>memory_statement.log && export GALAXY_MEMORY_MB || unset GALAXY_MEMORY_MB
[ "${GALAXY_MEMORY_MB_PER_SLOT--1}" -gt 0 ] 2>>memory_statement.log && export GALAXY_MEMORY_MB_PER_SLOT || unset GALAXY_MEMORY_MB_PER_SLOT
