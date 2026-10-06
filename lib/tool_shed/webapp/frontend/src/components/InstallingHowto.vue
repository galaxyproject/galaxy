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
`,
)
</script>

<template>
    <h2 class="shed-section-title">Install</h2>
    <p class="installing-text">
        Galaxy admins can install this repository from
        <strong>Admin &rarr; Tool Management &rarr; Install and Uninstall</strong>, or from the API with
        <a href="https://ephemeris.readthedocs.io/en/latest/commands/shed-tools.html">Ephemeris</a> or
        <a href="https://github.com/galaxyproject/ansible-galaxy-tools">Ansible Galaxy Tools</a> using this block for
        the latest revision:
    </p>
    <config-file-contents name="tools.yml" :contents="toolsYaml" what="Ephemeris tools configuration" />
    <p class="installing-text installing-more">
        New to this? See the <a :href="EPHEMERIS_TRAINING">tool installation training materials</a>.
    </p>
</template>

<style scoped>
.installing-text {
    margin: 0;
    font-size: 0.92rem;
}

.installing-more {
    color: var(--shed-muted);
}
</style>
