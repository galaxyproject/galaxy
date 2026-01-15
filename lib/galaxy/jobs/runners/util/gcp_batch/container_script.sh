#!/bin/bash
set -e
echo "=== Galaxy GCP Batch Job Execution ==="
echo "Job: ${job_id_tag}"
echo "Tool: ${tool_id}"
echo "Container: ${container_image}"
echo "Timestamp: $$(date)"
echo "Host: $$(hostname)"
echo ""

# Debug network and NFS connectivity
echo "=== Network and NFS Connectivity Debug ==="
echo "Testing NFS server connectivity: ${nfs_server}"
if ping -c 3 ${nfs_server} > /dev/null 2>&1; then
    echo "✓ NFS server is reachable via ping"
else
    echo "✗ NFS server is NOT reachable via ping"
fi

# Check if NFS client tools are available
echo "Checking NFS client availability:"
which mount.nfs4 || echo "mount.nfs4 not found - installing nfs-utils"
apt-get update -qq && apt-get install -y nfs-common > /dev/null 2>&1 || echo "Failed to install nfs-common"

# Check all mounts
echo "Current mounts:"
mount | grep -E "(nfs|${nfs_mount_path})" || echo "No NFS mounts found"

# Check NFS mount
if [ -d "${nfs_mount_path}" ]; then
    echo "✓ NFS mount point exists: ${nfs_mount_path}"

    if mount | grep "${nfs_mount_path}"; then
        echo "✓ NFS is mounted successfully"
        echo "NFS mount details:"
        df -h "${nfs_mount_path}"
        mount | grep "${nfs_mount_path}"
        echo ""

        # Fix NFS attribute caching by remounting with actimeo=0
        echo "=== Fixing NFS attribute caching ==="
        NFS_SERVER=$$(mount | grep "${nfs_mount_path}" | cut -d: -f1)
        NFS_PATH=$$(mount | grep "${nfs_mount_path}" | cut -d: -f2 | cut -d' ' -f1)
        echo "Remounting $$NFS_SERVER:$$NFS_PATH with actimeo=0 to disable attribute caching"

        # Remount with optimized options
        umount "${nfs_mount_path}" || echo "Warning: umount failed"
        mount -t nfs4 -o rw,hard,intr,rsize=1048576,wsize=1048576,actimeo=0 "$$NFS_SERVER:$$NFS_PATH" "${nfs_mount_path}"

        echo "NFS remounted with optimized options:"
        mount | grep "${nfs_mount_path}"
        echo ""

        # Wait a moment for NFS to sync
        sleep 2

        # Verify Galaxy job files are accessible
        if [ -f "${job_file}" ]; then
            echo "✓ Galaxy job script accessible: ${job_file}"
        else
            echo "✗ Galaxy job script NOT accessible: ${job_file}"
            echo "Available files in job directory:"
            ls -la "$$(dirname ${job_file})" || echo "Could not list job directory"

            # Try to find the job directory
            echo "Searching for job directory in NFS mount:"
            find "${nfs_mount_path}" -name "jobs_directory" -type d 2>/dev/null | head -5

            # List what's actually in the NFS root
            echo "Contents of NFS root:"
            ls -la "${nfs_mount_path}/" || echo "Could not list NFS root"

            exit 1
        fi

        # Set up environment variables for the container
        export GALAXY_SLOTS=${galaxy_slots}
        export GALAXY_MEMORY_MB=${galaxy_memory_mb}

        echo "Container environment:"
        echo "  GALAXY_SLOTS=$$GALAXY_SLOTS"
        echo "  GALAXY_MEMORY_MB=$$GALAXY_MEMORY_MB"
        echo ""

        echo "=== Preparing Volume Mounts ==="

        # Check CVMFS availability and trigger autofs mount
        echo "=== CVMFS Verification ==="
        if ls /cvmfs/data.galaxyproject.org/ >/dev/null 2>&1; then
            echo "✓ CVMFS data is accessible at /cvmfs/data.galaxyproject.org"
            echo "CVMFS contents (first 5 entries):"
            ls -la /cvmfs/data.galaxyproject.org/ | head -5
        else
            echo "✗ CVMFS data not accessible at /cvmfs/data.galaxyproject.org"
            echo "This may indicate CVMFS is not configured or the repository is unavailable"
            echo "Jobs requiring reference data may fail"
        fi
        echo ""

        echo "=== Starting Container Execution ==="
        # Run the Galaxy job script inside the container with all volume mounts
        docker run --rm ${docker_user_flag} \
            -v "${nfs_mount_path}:${nfs_mount_path}:rw" \
            ${docker_volume_args} \
            -w "$$(dirname ${job_file})" \
            -e GALAXY_SLOTS="$$GALAXY_SLOTS" \
            -e GALAXY_MEMORY_MB="$$GALAXY_MEMORY_MB" \
            -e HOME=/tmp \
            "${container_image}" /bin/bash "${job_file}"

        echo ""
        echo "=== Container execution completed ==="

    else
        echo "✗ NFS mount point exists but is not mounted"
        echo "Attempting manual NFS mount as fallback..."

        # Try manual NFS mount
        if mount -t nfs4 -o rw,hard,intr,rsize=1048576,wsize=1048576,actimeo=0 ${nfs_server}:${nfs_path} "${nfs_mount_path}"; then
            echo "✓ Manual NFS mount successful"
            mount | grep "${nfs_mount_path}"
        else
            echo "✗ Manual NFS mount failed"
            echo "Debug information:"
            echo "  NFS Server: ${nfs_server}"
            echo "  NFS Path: ${nfs_path}"
            echo "  Mount Path: ${nfs_mount_path}"
            exit 1
        fi
    fi
else
    echo "✗ NFS mount point does not exist: ${nfs_mount_path}"
    echo "Creating mount point and attempting manual mount..."
    mkdir -p "${nfs_mount_path}"

    # Try manual NFS mount
    if mount -t nfs4 -o rw,hard,intr,rsize=1048576,wsize=1048576,actimeo=0 ${nfs_server}:${nfs_path} "${nfs_mount_path}"; then
        echo "✓ Manual NFS mount successful after creating mount point"
        mount | grep "${nfs_mount_path}"
    else
        echo "✗ Manual NFS mount failed"
        echo "This indicates network connectivity or permission issues"
        exit 1
    fi
fi

echo "Galaxy job execution finished"
