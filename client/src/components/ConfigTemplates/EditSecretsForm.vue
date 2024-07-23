<script setup lang="ts">
import { type TemplateSummary } from "@/api/configTemplates";

import VaultSecret from "./VaultSecret.vue";
import FormCard from "@/components/Form/FormCard.vue";

interface Props {
    template: TemplateSummary;
    title: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "update", secretName: string, secretValue: string): void;
}>();

async function update(secretName: string, secretValue: string) {
    emit("update", secretName, secretValue);
}
</script>

<template>
    <FormCard :title="title">
        <template v-slot:body>
            <div v-for="secret in template.secrets" :key="secret.name">
                <VaultSecret
                    :label="secret.label || secret.name"
                    :name="secret.name"
                    :help="secret.help || ''"
                    :is-set="true"
                    @update="update">
                </VaultSecret>
            </div>
        </template>
    </FormCard>
</template>
