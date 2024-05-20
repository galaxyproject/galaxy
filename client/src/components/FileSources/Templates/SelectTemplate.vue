<script lang="ts" setup>
import type { FileSourceTemplateSummaries } from "@/api/fileSources";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";
import SelectTemplate from "@/components/ConfigTemplates/SelectTemplate.vue";

interface Props {
    templates: FileSourceTemplateSummaries;
}

defineProps<Props>();

const selectText =
    "Select file source template to create new file sources with. These templates are configured by your Galaxy administrator.";

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
            id-prefix="file-source"
            @onSubmit="handleSubmit">
        </SelectTemplate>
        <TemplateSummaryPopover
            v-for="template in templates"
            :key="template.id"
            :target="`file-source-template-button-${template.id}`"
            :template="template" />
    </div>
</template>
