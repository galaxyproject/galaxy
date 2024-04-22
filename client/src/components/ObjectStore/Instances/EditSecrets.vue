<script setup lang="ts">
import { computed } from "vue";

import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import { update } from "./services";
import type { UserConcreteObjectStore } from "./types";

import VaultSecret from "./VaultSecret.vue";
import FormCard from "@/components/Form/FormCard.vue";

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
    const args = { user_object_store_id: String(props.objectStore.id) };
    await update({ ...args, ...payload });
}
</script>
<template>
    <FormCard :title="title">
        <template v-slot:body>
            <div>
                <div v-for="secret in template.secrets" :key="secret.name">
                    <VaultSecret :name="secret.name" :help="secret.help || ''" :is-set="true" @update="onUpdate">
                    </VaultSecret>
                </div>
            </div>
        </template>
    </FormCard>
</template>
