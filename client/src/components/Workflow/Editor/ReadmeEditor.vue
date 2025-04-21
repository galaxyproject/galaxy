<script setup lang="ts">
import { faEdit, faEye, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BFormTextarea } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import Heading from "@/components/Common/Heading.vue";
import ToolHelpMarkdown from "@/components/Tool/ToolHelpMarkdown.vue";

const PLACEHOLDER_TEXT = [
    "The README is a markdown detailed description of what the workflow does.",
    "It is best to include descriptions of what kinds of data are required.",
    "Researchers looking for the workflow will see this text.",
    "Markdown is enabled.",
].join(" ");

const props = defineProps<{
    readme?: string;
    name?: string;
    logoUrl?: string;
}>();

const emit = defineEmits<{
    (e: "update:readmeCurrent", readme: string): void;
    (e: "exit"): void;
}>();

const readmeEdit = ref(true);
const readmeCurrent = ref(props.readme || "");

const readmePreviewMarkdown = computed(() => {
    let content = "";
    if (props.logoUrl) {
        content += `![${props.name || "workflow"} logo](${props.logoUrl})\n\n`;
    }
    if (readmeCurrent.value) {
        content += readmeCurrent.value;
    }
    return content;
});

watch(
    () => props.readme,
    (newValue) => {
        readmeCurrent.value = newValue ?? "";
    },
    { immediate: true }
);
</script>

<template>
    <div class="h-100 d-flex flex-column">
        <div class="d-flex flex-gapx-1">
            <Heading h3 separator inline size="sm" class="flex-grow-1 m-0">
                <span v-localize>Workflow Readme</span>
            </Heading>
            <BButtonGroup>
                <BButton size="sm" variant="outline-primary" :disabled="readmeEdit" @click="readmeEdit = true">
                    <FontAwesomeIcon :icon="faEdit" />
                    <span v-localize>Edit</span>
                </BButton>
                <BButton size="sm" variant="outline-primary" :disabled="!readmeEdit" @click="readmeEdit = false">
                    <FontAwesomeIcon :icon="faEye" />
                    <span v-localize>Preview</span>
                </BButton>
            </BButtonGroup>
            <BButton
                v-b-tooltip.hover.noninteractive
                size="sm"
                variant="outline-danger"
                title="Return to Workflow"
                @click="emit('exit')">
                <FontAwesomeIcon :icon="faTimes" />
                <span v-localize>Exit</span>
            </BButton>
        </div>
        <div v-if="readmeEdit" class="mt-2 d-flex flex-column">
            <BFormTextarea
                id="workflow-readme"
                v-model="readmeCurrent"
                size="lg"
                class="flex-grow-1 workflow-readme-textarea"
                :state="readmeCurrent.length > 0 ? null : false"
                no-resize
                :placeholder="PLACEHOLDER_TEXT"
                @keyup="emit('update:readmeCurrent', readmeCurrent)" />
        </div>
        <ToolHelpMarkdown v-else class="mt-2 overflow-auto" :content="readmePreviewMarkdown" />
    </div>
</template>

<style scoped>
.workflow-readme-textarea {
    font: 14px/1.7 Menlo, Consolas, Monaco, "Andale Mono", monospace;
}
</style>
