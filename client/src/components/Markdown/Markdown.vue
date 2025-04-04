<script setup lang="ts">
import { faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";

import { parseMarkdown } from "./parse";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import SectionWrapper from "@/components/Markdown/Sections/SectionWrapper.vue";
import StsDownloadButton from "@/components/StsDownloadButton.vue";

// Props
interface MarkdownConfig {
    content?: string;
    errors?: Array<{ error?: string; line?: string }>;
    generate_time?: string;
    generate_version?: string;
    id?: string;
    markdown?: string;
    model_class?: string;
    title?: string;
    update_time?: string;
}

const props = defineProps<{
    markdownConfig: MarkdownConfig;
    enable_beta_markdown_export?: boolean;
    downloadEndpoint: string;
    readOnly?: boolean;
    exportLink?: string;
}>();

// Refs and data
const markdownObjects = ref<any[]>([]);
const markdownErrors = ref<any[]>([]);
const loading = ref(true);

// Computed properties
const effectiveExportLink = computed(() => (props.enable_beta_markdown_export ? props.exportLink : null));

const updateTime = computed(() => {
    const generateTime = props.markdownConfig.update_time;
    if (generateTime) {
        const formattedTime = generateTime.endsWith("Z") ? generateTime : `${generateTime}Z`;
        const date = new Date(formattedTime);
        return date.toLocaleString("default", {
            day: "numeric",
            month: "long",
            year: "numeric",
            hour: "numeric",
            minute: "numeric",
            timeZone: "UTC",
            timeZoneName: "short",
        });
    }
    return "";
});

// Methods
function initConfig() {
    const config = props.markdownConfig;
    if (Object.keys(config).length) {
        const markdown = config.content || config.markdown || "";
        markdownErrors.value = config.errors || [];
        markdownObjects.value = parseMarkdown(markdown);
        loading.value = false;
    }
}

// Watchers
watch(() => props.markdownConfig, initConfig);

// Lifecycle hooks
onMounted(() => {
    initConfig();
});
</script>

<template>
    <div class="markdown-wrapper">
        <LoadingSpan v-if="loading" />
        <div v-else class="d-flex flex-column">
            <div class="d-flex flex-column sticky-top bg-white">
                <div class="d-flex">
                    <Heading v-localize h1 separator inline size="md" class="flex-grow-1">
                        {{ markdownConfig.title || markdownConfig.model_class }}
                    </Heading>
                    <div>
                        <StsDownloadButton
                            v-if="effectiveExportLink"
                            class="markdown-pdf-export"
                            :fallback-url="exportLink"
                            :download-endpoint="downloadEndpoint"
                            size="small"
                            title="Generate PDF"
                            color="blue"
                            outline />
                        <BButton
                            v-if="!readOnly"
                            v-b-tooltip.hover
                            class="markdown-edit"
                            role="button"
                            size="sm"
                            title="Edit Markdown"
                            variant="outline-primary"
                            @click="$emit('onEdit')">
                            Edit
                            <FontAwesomeIcon :icon="faEdit" />
                        </BButton>
                    </div>
                </div>
            </div>
            <div class="flex-grow-1 w-75 mx-auto">
                <b-alert v-if="markdownErrors.length > 0" variant="warning" show>
                    <div v-for="(obj, index) in markdownErrors" :key="index" class="mb-1">
                        <h2 class="h-text">{{ obj.error || "Error" }}</h2>
                        {{ obj.line }}
                    </div>
                </b-alert>
                <div v-for="(obj, index) in markdownObjects" :key="index" class="markdown-component py-2">
                    <SectionWrapper :name="obj.name" :content="obj.content" />
                </div>
            </div>
            <div class="d-flex justify-content-between p-1">
                <small v-if="updateTime" class="text-break">Last updated on {{ updateTime }}</small>
                <small class="text-break">Identifier: {{ markdownConfig.id }}</small>
            </div>
        </div>
    </div>
</template>
