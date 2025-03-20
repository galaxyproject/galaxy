<script setup lang="ts">
import { computed } from "vue";

import { GalaxyApi } from "@/api";
import type { UserFileSourceModel } from "@/api/fileSources";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { rethrowSimple } from "@/utils/simple-error";

import InstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

const fileSourceTemplatesStore = useFileSourceTemplatesStore();

interface Props {
    fileSource: UserFileSourceModel;
}

const props = defineProps<Props>();
const routeEdit = computed(() => `/file_source_instances/${props.fileSource.uuid}/edit`);
const routeUpgrade = computed(() => `/file_source_instances/${props.fileSource.uuid}/upgrade`);
const isUpgradable = computed(() =>
    fileSourceTemplatesStore.canUpgrade(props.fileSource.template_id, props.fileSource.template_version)
);

async function onRemove() {
    const { error } = await GalaxyApi().PUT("/api/file_source_instances/{uuid}", {
        params: { path: { uuid: props.fileSource.uuid } },
        body: {
            hidden: true,
        },
    });

    if (error) {
        rethrowSimple(error);
    }

    emit("entryRemoved");
}

const emit = defineEmits<{
    (e: "entryRemoved"): void;
    (e: "test"): void;
}>();
</script>

<template>
    <InstanceDropdown
        prefix="file-source"
        :name="fileSource.name || ''"
        :is-upgradable="isUpgradable"
        :route-upgrade="routeUpgrade"
        :route-edit="routeEdit"
        @test="emit('test')"
        @remove="onRemove" />
</template>
