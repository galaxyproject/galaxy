<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { RouterLink } from "vue-router";

import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

interface Props {
    selectedRepository?: BrowsableFilesSourcePlugin;
    isPrivateFileSource?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    selectedRepository: undefined,
    isPrivateFileSource: undefined,
});

const repositoryName = props.selectedRepository?.label ?? "the selected repository";
</script>

<template>
    <BAlert show variant="info">
        If you haven't done it yet. You may need to setup your credentials for {{ repositoryName }}

        <span v-if="isPrivateFileSource && selectedRepository">
            in your
            <RouterLink :to="`/file_source_instances/${selectedRepository.id}/edit`" target="_blank">
                Remote File Source settings
            </RouterLink>
        </span>
        <span v-else>
            <span v-if="!isPrivateFileSource">
                in your <RouterLink to="/user/information" target="_blank">preferences page</RouterLink>
            </span>
            or in your <RouterLink to="/file_sources/index" target="_blank"> Remote File Sources </RouterLink> section
        </span>
        to be able to export. You can also define some default options for the export in those settings, like the public
        name you want to associate with your records.
    </BAlert>
</template>
