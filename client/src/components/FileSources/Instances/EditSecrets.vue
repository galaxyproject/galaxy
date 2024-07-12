<script setup lang="ts">
import { computed } from "vue";

import type { FileSourceTemplateSummary, UserFileSourceModel } from "@/api/fileSources";

import { update } from "./services";

import EditSecretsForm from "@/components/ConfigTemplates/EditSecretsForm.vue";

interface Props {
    fileSource: UserFileSourceModel;
    template: FileSourceTemplateSummary;
}
const props = defineProps<Props>();
const title = computed(() => `Update File Source ${props.fileSource?.name} Secrets`);

async function onUpdate(secretName: string, secretValue: string) {
    const payload = {
        secret_name: secretName,
        secret_value: secretValue,
    };
    const args = { user_file_source_id: String(props.fileSource.uuid) };
    await update({ ...args, ...payload });
}
</script>
<template>
    <EditSecretsForm :title="title" :template="template" @update="onUpdate" />
</template>
