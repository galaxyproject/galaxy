<script lang="ts" setup>
import { BButton, BButtonGroup, BCol, BRow } from "bootstrap-vue";

import type { TemplateSummary } from "@/api/configTemplates";

interface Props {
    selectText: string;
    idPrefix: string;
    templates: TemplateSummary[];
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "onSubmit", id: string): void;
}>();

async function handleSubmit(templateId: string) {
    emit("onSubmit", templateId);
}
</script>

<template>
    <BRow>
        <BCol cols="7">
            <BButtonGroup vertical size="lg" style="width: 100%">
                <BButton
                    v-for="template in templates"
                    :id="`${idPrefix}-template-button-${template.id}`"
                    :key="template.id"
                    :class="`${idPrefix}-template-select-button`"
                    :data-template-id="template.id"
                    @click="handleSubmit(template.id)"
                    >{{ template.name }}
                </BButton>
            </BButtonGroup>
        </BCol>
        <BCol cols="5">
            <p v-localize style="float: right" :class="`${idPrefix}-template-select-help`">
                {{ selectText }}
            </p>
        </BCol>
    </BRow>
</template>
