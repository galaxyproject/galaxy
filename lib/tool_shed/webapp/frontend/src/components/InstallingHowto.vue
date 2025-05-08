<script setup lang="ts">
import { computed } from "vue"
import ConfigFileContents from "@/components/ConfigFileContents.vue"
import { EPHEMERIS_TRAINING } from "@/constants"

interface Props {
    repositoryName: string
    repositoryOwner: string
}

const props = defineProps<Props>()

const toolsYaml = computed(
    () =>
        `tools:
- name: ${props.repositoryName}
  owner: ${props.repositoryOwner}
`
)
</script>

<template>
    <div class="repository-select-label text-h5 q-mr-lg">Installing</div>
    This repository can be installed by Galaxy admins by searching for it in the
    <code>Admin -> Tool Management -> Install and Uninstall</code> and choosing to install it. It can also be installed
    using the Galaxy API via
    <a href="https://ephemeris.readthedocs.io/en/latest/commands/shed-tools.html">Ephemeris</a> or
    <a href="https://github.com/galaxyproject/ansible-galaxy-tools">Ansible Galaxy Tools</a>. The following YAML block
    will instruct these tools to install the latest revision of this repository.
    <config-file-contents name="tools.yml" :contents="toolsYaml" what="Ephemeris tools configuration" />
    Be sure to check out the <a :href="EPHEMERIS_TRAINING">tool installation training materials</a> for more
    information.
</template>
