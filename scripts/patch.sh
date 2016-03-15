#!/bin/bash
set -e

echo "THIS SCRIPT IS ONLY SAFE TO RUN IF YOUR BRANCHES ARE ALL MERGED FORWARD"
echo "THIS SCRIPT DISCARDS UPSTREAM BRANCH CHANGES TO RESOLVE MERGE CONFLICTS"
echo "YOU HAVE BEEN WARNED"

patchbase=../patch
clone=galaxy

declare -a releases=("14.10" "15.01" "15.03" "15.05" "15.07" "15.10" "16.01" "dev")
declare -a patches=("safe_relpath-RELEASEU.patch" "gx_history_import-RELEASEU.patch" "gx_objectstore_relpath-RELEASEU.patch" "gx_sample_transfer-RELEASEU.patch" "ts_browse_symlink_relpath-RELEASEU.patch" "ts_upload_symlink_relpath-RELEASEU.patch")
declare -a patchmsgs=('Add a safe_relpath util function for ensuring a path does not reference an absolute or parent directory' 'Security fixes for history imports' 'Security fixes for object store paths' 'Remove sample tracking manual external service transfer due to security concerns' 'Security fixes for tool shed repository browsing' 'Security fixes for tool shed hg push and capsule/tarball uploads')

[ -d $clone ] || git clone git@github.com:natefoo/galaxy.git $clone
cd $clone

for (( i=0; i < ${#releases[@]}; i++ )); do
    release=${releases[$i]}
    releaseu=${release/./_}
    branch=release_${release}
    [ $release == "dev" ] && branch=dev
    git checkout ${branch}
    for (( j=0; j < ${#patches[@]}; j++ )); do
        patchf=${patchbase}/${patches[$j]}
        patchf=${patchf/RELEASEU/$releaseu}
        if [ -f ${patchf} ]; then
            echo "Applying patch $patchf"
            patch -p1 < ${patchf}
            git add -u
            git commit -m "${patchmsgs[$j]}"
        else
            echo "WARNING: no such patch: $patchf"
        fi
    done
    if [ $i -gt 0 ]; then
        prevrel=${releases[$(( $i - 1 ))]}
        msg="Merge branch 'release_${prevrel}' into ${branch}"
        echo "$msg"
        if ! git merge -m "$msg" release_${prevrel}; then
            while read status fp; do
                echo 'Handling merge conflicts by restoring "our" version'
                if [ $status == "UU" ]; then
                    echo "git checkout --ours $fp"
                    git checkout --ours $fp
                fi
            done < <(git status --short)
            git add -u
            git commit -m "$msg"
        fi
    fi
done
