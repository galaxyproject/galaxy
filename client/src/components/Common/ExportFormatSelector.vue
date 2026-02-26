<script setup lang="ts">
import { BCard, BCardGroup, BCardImg, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";
import type { ExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";
import { useMarkdown } from "@/composables/markdown";

import ExternalLink from "@/components/ExternalLink.vue";

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

interface Props {
    plugins: ExportPlugin[];
    modelValue: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:model-value", value: string): void;
}>();

function selectPlugin(plugin: ExportPlugin) {
    emit("update:model-value", plugin.exportParams.modelStoreFormat);
}

function isSelected(plugin: ExportPlugin): boolean {
    return props.modelValue === plugin.exportParams.modelStoreFormat;
}
</script>

<template>
    <BCardGroup deck>
        <BCard
            v-for="plugin in plugins"
            :key="plugin.id"
            :data-export-format="plugin.exportParams.modelStoreFormat"
            class="export-format-card"
            :border-variant="borderVariant(isSelected(plugin))"
            @click="selectPlugin(plugin)">
            <BCardTitle>
                <b>{{ plugin.title }}</b>
            </BCardTitle>
            <div v-if="plugin.img">
                <BCardImg :src="plugin.img" :alt="plugin.title" class="export-format-img" />
                <br />
                <ExternalLink v-if="plugin.url" :href="plugin.url">
                    <b>Learn more</b>
                </ExternalLink>
            </div>
            <div v-else v-html="renderMarkdown(plugin.markdownDescription)" />
        </BCard>
    </BCardGroup>
</template>

<style scoped lang="scss">
.export-format-card {
    cursor: pointer;
    transition: border-color 0.15s ease-in-out;

    &:hover {
        border-color: var(--bs-primary);
    }
}

.export-format-img {
    height: auto;
    width: auto;
    max-height: 100px;
    max-width: 100%;
    max-inline-size: -webkit-fill-available;
}
</style>
