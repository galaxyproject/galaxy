<script setup lang="ts">
import { computed } from "vue";

import { GalaxyApi } from "@/api";
import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";
import { rethrowSimple } from "@/utils/simple-error";

import EditSecretsForm from "@/components/ConfigTemplates/EditSecretsForm.vue";

interface Props {
    fileSource: UserFileSourceModel;
    template: FileSourceTemplateSummary;
}
const props = defineProps<Props>();
const title = computed(() => `Update File Source ${props.fileSource?.name} Secrets`);

async function onUpdate(secretName: string, secretValue: string) {
    const { error } = await GalaxyApi().PUT("/api/file_source_instances/{uuid}", {
        params: { path: { uuid: props.fileSource.uuid } },
        body: {
            secret_name: secretName,
            secret_value: secretValue,
        },
    });

    if (error) {
        rethrowSimple(error);
    }
}
</script>
<template>
    <EditSecretsForm :title="title" :template="template" @update="onUpdate" />
</template>
