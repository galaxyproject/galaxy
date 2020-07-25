#!/bin/bash

git diff --name-status "$PR_BASE" "$PR_HEAD"

# Abort if anything but modified and added
abort=$(git diff --name-status "$PR_BASE" "$PR_HEAD" | cut -c1 | grep -E "C|D|R|T|U|X|B" )

echo "Starting"

if [[ ! -n $abort ]]; then

    curl -O https://gist.githubusercontent.com/almahmoud/a67fb678b76c901e19385f85d02ef8ca/raw/2388c72efe6aa0c0757d76e9b6828f05b6f4b410/values.yaml

    helm repo add gxy https://raw.githubusercontent.com/cloudve/helm-charts/master/

    echo "Starting making list"
    git diff --name-only "$PR_BASE" "$PR_HEAD" > filelist

    while IFS= read -r line; do echo -n $line | base64; done < filelist > encfilelist
    sed -i -e 's/\=//g' encfilelist
    sed -E 's#.+#--set-file configs."#g' filelist > start
    sed -E 's#.+#=#g' filelist > middle
    paste -d "\0\"" start encfilelist middle filelist > setfilelist
    PROJMAN_SET=$(paste -s -d ' ' setfilelist)

    echo helm upgrade --install "galaxy-preview-injection-$PR_NUM" gxy/projman --set projectName="galaxy-$PR_NUM" $PROJMAN_SET
    helm upgrade --install galaxy-preview-injection-$PR_NUM gxy/projman --set projectName="galaxy-$PR_NUM" $PROJMAN_SET

    cat <<EOF > vols.yaml
extraVolumes:
  - name: "code-injection"
    configMap:
      name: galaxy-$PR_NUM-projman-configs
      items:
EOF

    sed -E 's#--set-file configs.("[^"]+")=(.+)#        - key: \1\n          path: "\2"#g' setfilelist >> vols.yaml

    cat <<EOF >> vols.yaml
extraVolumeMounts:
  - name: code-injection
    mountPath: "/galaxy/server"
EOF

    echo helm upgrade --install "galaxy-preview-$PR_NUM" gxy/galaxy -f values.yaml -f vols.yaml
    helm upgrade --install galaxy-preview-$PR_NUM gxy/galaxy -f values.yaml -f vols.yaml

fi

