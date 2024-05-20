<script setup lang="ts">
import { computed } from "vue";

import type { UserFileSourceModel } from "@/api/fileSources";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";

import InstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

const fileSourceTemplatesStore = useFileSourceTemplatesStore();

interface Props {
    fileSource: UserFileSourceModel;
}

const props = defineProps<Props>();
const routeEdit = computed(() => `/file_source_instances/${props.fileSource.id}/edit`);
const routeUpgrade = computed(() => `/file_source_instances/${props.fileSource.id}/upgrade`);
const isUpgradable = computed(() =>
    fileSourceTemplatesStore.canUpgrade(props.fileSource.template_id, props.fileSource.template_version)
);
</script>

<template>
    <InstanceDropdown
        prefix="file-source"
        :name="fileSource.name || ''"
        :is-upgradable="isUpgradable"
        :route-upgrade="routeUpgrade"
        :route-edit="routeEdit" />
</template>
