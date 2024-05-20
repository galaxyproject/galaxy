<script lang="ts" setup>
import type { ObjectStoreTemplateSummaries } from "./types";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";
import SelectTemplate from "@/components/ConfigTemplates/SelectTemplate.vue";

interface SelectTemplateProps {
    templates: ObjectStoreTemplateSummaries;
}

defineProps<SelectTemplateProps>();

const selectText =
    "Select storage location template to create new storage location with. These templates are configured by your Galaxy administrator.";

const emit = defineEmits<{
    (e: "onSubmit", id: string): void;
}>();

async function handleSubmit(templateId: string) {
    emit("onSubmit", templateId);
}
</script>

<template>
    <div>
        <SelectTemplate
            :templates="templates"
            :select-text="selectText"
            id-prefix="object-store"
            @onSubmit="handleSubmit">
        </SelectTemplate>
        <TemplateSummaryPopover
            v-for="template in templates"
            :key="template.id"
            :target="`object-store-template-button-${template.id}`"
            :template="template" />
    </div>
</template>
