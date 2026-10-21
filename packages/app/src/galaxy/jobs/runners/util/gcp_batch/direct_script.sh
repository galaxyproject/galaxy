#!/bin/bash
set -e
echo "=== Galaxy GCP Batch Job Execution (Direct) ==="
echo "Job: ${job_id_tag}"
echo "Tool: ${tool_id}"
echo "Timestamp: $$(date)"
echo "Host: $$(hostname)"
echo ""

# Check NFS mount
if [ -d "${nfs_mount_path}" ]; then
    echo "✓ NFS mount point exists: ${nfs_mount_path}"

    if mount | grep "${nfs_mount_path}"; then
        echo "✓ NFS is mounted successfully"

        # Verify Galaxy job files are accessible
        if [ -f "${job_file}" ]; then
            echo "✓ Galaxy job script accessible: ${job_file}"
        else
            echo "✗ Galaxy job script NOT accessible: ${job_file}"
            exit 1
        fi

        # Set up environment
        export GALAXY_SLOTS=${galaxy_slots}
        export GALAXY_MEMORY_MB=${galaxy_memory_mb}

        echo "Environment:"
        echo "  GALAXY_SLOTS=$$GALAXY_SLOTS"
        echo "  GALAXY_MEMORY_MB=$$GALAXY_MEMORY_MB"
        echo ""

        echo "=== Starting Direct Execution ==="
        # Execute the Galaxy job script directly
        cd "$$(dirname ${job_file})"
        /bin/bash "${job_file}"

        echo "=== Direct execution completed ==="

    else
        echo "✗ NFS mount point exists but is not mounted"
        exit 1
    fi
else
    echo "✗ NFS mount point does not exist: ${nfs_mount_path}"
    exit 1
fi

echo "Galaxy job execution finished"
