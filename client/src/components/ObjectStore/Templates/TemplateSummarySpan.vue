<script setup lang="ts">
import { computed } from "vue";

import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();

interface Props {
    templateId: string;
    templateVersion: number;
}

const props = defineProps<Props>();

const template = computed(() => objectStoreTemplatesStore.getTemplate(props.templateId, props.templateVersion));
const target = `template-summary-span-${crypto.randomUUID()}`;
objectStoreTemplatesStore.ensureTemplates();
</script>

<template>
    <span>
        <span v-if="template">
            <span :id="target">
                {{ template.name }}
            </span>
            <TemplateSummaryPopover :template="template" :target="target" />
        </span>
        <span v-else> Loading template information for {{ templateId }} {{ templateVersion }} </span>
    </span>
</template>
