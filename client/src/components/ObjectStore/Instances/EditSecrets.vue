<script setup lang="ts">
import { computed } from "vue";

import { GalaxyApi } from "@/api";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";
import { rethrowSimple } from "@/utils/simple-error";

import type { UserConcreteObjectStore } from "./types";

import EditSecretsForm from "@/components/ConfigTemplates/EditSecretsForm.vue";

interface Props {
    objectStore: UserConcreteObjectStore;
    template: ObjectStoreTemplateSummary;
}
const props = defineProps<Props>();
const title = computed(() => `Update Galaxy Storage ${props.objectStore?.name} Secrets`);

async function onUpdate(secretName: string, secretValue: string) {
    const { error } = await GalaxyApi().PUT("/api/object_store_instances/{uuid}", {
        params: { path: { uuid: props.objectStore.uuid } },
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
