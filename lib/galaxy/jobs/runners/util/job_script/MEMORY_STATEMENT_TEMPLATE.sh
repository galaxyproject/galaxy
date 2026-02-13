if [ -z "$GALAXY_MEMORY_MB" -a -n "$SLURM_JOB_ID" ]; then
    GALAXY_MEMORY_MB=`scontrol -do show job "$SLURM_JOB_ID" | sed 's/.*\( \|^\)Mem=\([0-9][0-9]*\)\( \|$\).*/\2/p;d'` 2>$metadata_directory/memory_statement.log
fi
if [ -n "$SGE_HGR_h_vmem" ]; then
    GALAXY_MEMORY_MB_PER_SLOT=`echo "$SGE_HGR_h_vmem" | sed 's/G$/ * 1024/' | bc | cut -d"." -f1` 2>$metadata_directory/memory_statement.log
fi

if [ -n "$GALAXY_MEMORY_MB" -a -n "${GALAXY_MEMORY_MB_OVERHEAD:-}" ]; then
    GALAXY_MEMORY_MB=$(($GALAXY_MEMORY_MB - GALAXY_MEMORY_MB_OVERHEAD))
    [ "$GALAXY_MEMORY_MB" -gt "${GALAXY_MEMORY_MB_FLOOR:=256}" ] || GALAXY_MEMORY_MB=$GALAXY_MEMORY_MB_FLOOR
fi

if [ -z "$GALAXY_MEMORY_MB_PER_SLOT" -a -n "$GALAXY_MEMORY_MB" ]; then
    GALAXY_MEMORY_MB_PER_SLOT=$(($GALAXY_MEMORY_MB / $GALAXY_SLOTS))
elif [ -z "$GALAXY_MEMORY_MB" -a -n "$GALAXY_MEMORY_MB_PER_SLOT" ]; then
    GALAXY_MEMORY_MB=$(($GALAXY_MEMORY_MB_PER_SLOT * $GALAXY_SLOTS))
fi

if [ -n "$GALAXY_MEMORY_MB" -a -z "$GALAXY_MEMORY_GB" ]; then
    GALAXY_MEMORY_GB=$(($GALAXY_MEMORY_MB / 1024))
    [ "$GALAXY_MEMORY_GB" -gt 0 ] || GALAXY_MEMORY_GB=1
fi
if [ -n "$GALAXY_MEMORY_GB" -a -z "$GALAXY_MEMORY_GB_PER_SLOT" ]; then
    GALAXY_MEMORY_GB_PER_SLOT=$(($GALAXY_MEMORY_GB / $GALAXY_SLOTS))
    [ "$GALAXY_MEMORY_GB_PER_SLOT" -gt 0 ] || GALAXY_MEMORY_GB_PER_SLOT=1
fi

[ "${GALAXY_MEMORY_MB--1}" -gt 0 ] 2>>$metadata_directory/memory_statement.log && export GALAXY_MEMORY_MB || unset GALAXY_MEMORY_MB
[ "${GALAXY_MEMORY_MB_PER_SLOT--1}" -gt 0 ] 2>>$metadata_directory/memory_statement.log && export GALAXY_MEMORY_MB_PER_SLOT || unset GALAXY_MEMORY_MB_PER_SLOT
[ "${GALAXY_MEMORY_GB--1}" -gt 0 ] 2>>$metadata_directory/memory_statement.log && export GALAXY_MEMORY_GB || unset GALAXY_MEMORY_GB
[ "${GALAXY_MEMORY_GB_PER_SLOT--1}" -gt 0 ] 2>>$metadata_directory/memory_statement.log && export GALAXY_MEMORY_GB_PER_SLOT || unset GALAXY_MEMORY_GB_PER_SLOT
