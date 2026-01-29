#!/bin/sh

##
## CHANGE ME to galaxy's database name
## 
DATABASE=galaxyprod

##
## AWK script to extract the relevant fields of SGE's qacct report
##   and write them all in one line.
AWKSCRIPT='
$1=="jobnumber" { job_number = $2 }
$1=="qsub_time" { qsub_time = $2 }
$1=="start_time" { start_time = $2 }
$1=="end_time" { end_time = $2 
        print job_number, qsub_time, start_time, end_time
}
'

FIFO=$(mktemp -u) || exit 1
mkfifo "$FIFO" || exit 1

##
## Write the SGE/QACCT job report into a pipe
## (later will be loaded into a temporary table)
qacct -j |
    egrep "jobnumber|qsub_time|start_time|end_time" |
    sed 's/  */\t/'  |
    awk -v FS="\t" -v OFS="\t" "$AWKSCRIPT" |
    grep -v -- "-/-" > "$FIFO" &

##
##  The SQL to generate the report
##
SQL="
--
-- Temporary table which contains the qsub/start/end times, based on SGE's qacct report.
--
CREATE TEMPORARY TABLE sge_times (
  sge_job_id INTEGER PRIMARY KEY,
  qsub_time TIMESTAMP WITHOUT TIME ZONE,
  start_time TIMESTAMP WITHOUT TIME ZONE,
  end_time TIMESTAMP WITHOUT TIME ZONE
);

COPY sge_times FROM '$FIFO' ;

--
-- Temporary table which contains a unified view of all galaxy jobs.
-- for each job:
--   the user name, total input size (bytes), and input file types, DBKEY
--   creation time, update time, SGE job runner parameters
-- If a job had more than one input file, then some parameters might not be accurate (e.g. DBKEY)
-- as one will be chosen arbitrarily
CREATE TEMPORARY TABLE job_input_sizes AS
SELECT
 job.job_runner_external_id as job_runner_external_id,
 min(job.id) as job_id,
 min(job.create_time) as job_create_time,
 min(job.update_time) as job_update_time,
 min(galaxy_user.email) as email,
 min(job.tool_id) as tool_name,
-- This hack requires a user-custom aggregate function, comment it out for now
-- textcat_all(hda.extension || ' ') as file_types,
 sum(dataset.file_size) as total_input_size,
 count(dataset.file_size) as input_dataset_count,
 min(job.job_runner_name) as job_runner_name,
-- This hack tries to extract the DBKEY attribute from the metadata JSON string
 min(substring(encode(metadata,'escape') from '\"dbkey\": \\\\[\"(.*?)\"\\\\]')) as dbkey
FROM
 job,
 galaxy_user,
 job_to_input_dataset,
 history_dataset_association hda,
 dataset
WHERE
 job.user_id = galaxy_user.id
 AND
 job.id = job_to_input_dataset.job_id
 AND
 hda.id = job_to_input_dataset.dataset_id
 AND
 dataset.id = hda.dataset_id
 AND
 job.job_runner_external_id is not NULL
GROUP BY
 job.job_runner_external_id;


--
-- Join the two temporary tables, create a nice report
--
SELECT
 job_input_sizes.job_runner_external_id as sge_job_id,
 job_input_sizes.job_id as galaxy_job_id,
 job_input_sizes.email,
 job_input_sizes.tool_name,
-- ## SEE previous query for commented-out filetypes field
-- job_input_sizes.file_types,
 job_input_sizes.job_runner_name as sge_params,
 job_input_sizes.dbkey,
 job_input_sizes.total_input_size,
 job_input_sizes.input_dataset_count,
 job_input_sizes.job_update_time - job_input_sizes.job_create_time as galaxy_total_time,
 sge_times.end_time - sge_times.qsub_time as sge_total_time,
 sge_times.start_time - sge_times.qsub_time as sge_waiting_time,
 sge_times.end_time - sge_times.start_time as sge_running_time,
 job_input_sizes.job_create_time as galaxy_job_create_time
-- ## no need to show the exact times, the deltas (above) are informative enough
-- job_input_sizes.job_update_time as galaxy_job_update_time,
-- sge_times.qsub_time as sge_qsub_time,
-- sge_times.start_time as sge_start_time,
-- sge_times.end_time as sge_end_time
FROM
 job_input_sizes
LEFT OUTER JOIN
 SGE_TIMES
ON (job_input_sizes.job_runner_external_id = sge_times.sge_job_id)
ORDER BY
 galaxy_job_create_time
 
"

echo "$SQL" | psql --pset "footer=off" -F"  " -A --quiet "$DATABASE"


