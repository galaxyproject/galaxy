<script setup lang="ts">
import { computed } from "vue";

import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import { update } from "./services";
import type { UserConcreteObjectStore } from "./types";

import EditSecretsForm from "@/components/ConfigTemplates/EditSecretsForm.vue";

interface Props {
    objectStore: UserConcreteObjectStore;
    template: ObjectStoreTemplateSummary;
}
const props = defineProps<Props>();
const title = computed(() => `Update Storage Location ${props.objectStore?.name} Secrets`);

async function onUpdate(secretName: string, secretValue: string) {
    const payload = {
        secret_name: secretName,
        secret_value: secretValue,
    };
    const args = { user_object_store_id: String(props.objectStore.uuid) };
    await update({ ...args, ...payload });
}
</script>
<template>
    <EditSecretsForm :title="title" :template="template" @update="onUpdate" />
</template>
