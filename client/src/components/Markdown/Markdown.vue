<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faDownload, faEdit } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, ref, watch } from "vue";

import { useWorkflowStore } from "@/stores/workflowStore";

import { parseMarkdown } from "./parse";

import MarkdownDefault from "./Sections/MarkdownDefault.vue";
import MarkdownGalaxy from "./Sections/MarkdownGalaxy.vue";
import MarkdownVega from "./Sections/MarkdownVega.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import StsDownloadButton from "@/components/StsDownloadButton.vue";

library.add(faDownload, faEdit);

// Props
interface MarkdownConfig {
    generate_time?: string;
    generate_version?: string;
    content?: string;
    markdown?: string;
    errors?: Array<{ error?: string; line?: string }>;
    history_datasets?: Record<string, unknown>;
    histories?: Record<string, unknown>;
    history_dataset_collections?: Record<string, unknown>;
    workflows?: Record<string, unknown>;
    invocations?: Record<string, unknown>;
    id?: string;
    title?: string;
    model_class?: string;
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
const datasets = ref<Record<string, unknown>>({});
const histories = ref<Record<string, unknown>>({});
const collections = ref<Record<string, unknown>>({});
const workflows = ref<Record<string, unknown>>({});
const invocations = ref<Record<string, unknown>>({});
const loading = ref(true);
const workflowID = ref("");

// Workflow Store
const workflowStore = useWorkflowStore();
const fetchWorkflowForInstanceId = workflowStore.fetchWorkflowForInstanceId;
const getStoredWorkflowByInstanceId = workflowStore.getStoredWorkflowByInstanceId;

// Computed properties
const effectiveExportLink = computed(() => (props.enable_beta_markdown_export ? props.exportLink : null));

const time = computed(() => {
    const generateTime = props.markdownConfig.generate_time;
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
    return "unavailable";
});

const version = computed(() => props.markdownConfig.generate_version || "Unknown Galaxy Version");

const workflowVersions = computed(() => getStoredWorkflowByInstanceId(workflowID.value));

// Methods
function initConfig() {
    const config = props.markdownConfig;
    if (Object.keys(config).length) {
        const markdown = config.content || config.markdown || "";
        markdownErrors.value = config.errors || [];
        markdownObjects.value = parseMarkdown(markdown);
        datasets.value = config.history_datasets || {};
        histories.value = config.histories || {};
        collections.value = config.history_dataset_collections || {};
        workflows.value = config.workflows || {};
        invocations.value = config.invocations || {};
        workflowID.value = Object.keys(config.workflows || {})[0] || "";
        loading.value = false;
    }
}

// Watchers
watch(() => props.markdownConfig, initConfig);

// Lifecycle hooks
onMounted(() => {
    initConfig();
    fetchWorkflowForInstanceId(workflowID.value);
});
</script>

<template>
    <div class="markdown-wrapper">
        <LoadingSpan v-if="loading" />
        <div v-else>
            <div>
                <StsDownloadButton
                    v-if="effectiveExportLink"
                    class="float-right markdown-pdf-export"
                    :fallback-url="exportLink"
                    :download-endpoint="downloadEndpoint"
                    size="sm"
                    title="Generate PDF" />
                <b-button
                    v-if="!readOnly"
                    v-b-tooltip.hover
                    class="float-right markdown-edit mr-2"
                    role="button"
                    size="sm"
                    title="Edit Markdown"
                    @click="$emit('onEdit')">
                    Edit
                    <FontAwesomeIcon icon="edit" />
                </b-button>
                <h1 class="float-right align-middle mr-2 mt-1 h-md">Galaxy {{ markdownConfig.model_class }}</h1>
                <span class="float-left font-weight-light">
                    <h1 class="text-break align-middle">
                        Title: {{ markdownConfig.title || markdownConfig.model_class }}
                    </h1>
                    <h2 v-if="workflowVersions" class="text-break align-middle">
                        Workflow Checkpoint: {{ workflowVersions.version }}
                    </h2>
                </span>
            </div>
            <b-badge variant="info" class="w-100 rounded mb-3 white-space-normal">
                <div class="float-left m-1 text-break">Generated with Galaxy {{ version }} on {{ time }}</div>
                <div class="float-right m-1">Identifier: {{ markdownConfig.id }}</div>
            </b-badge>
            <div>
                <b-alert v-if="markdownErrors.length > 0" variant="warning" show>
                    <div v-for="(obj, index) in markdownErrors" :key="index" class="mb-1">
                        <h2 class="h-text">{{ obj.error || "Error" }}</h2>
                        {{ obj.line }}
                    </div>
                </b-alert>
            </div>
            <div v-for="(obj, index) in markdownObjects" :key="index" class="markdown-components">
                <MarkdownDefault v-if="obj.name === 'markdown'" :content="obj.content" />
                <MarkdownVega v-else-if="obj.name === 'vega'" :content="obj.content" />
                <MarkdownGalaxy
                    v-else-if="obj.name === 'galaxy'"
                    :content="obj.content"
                    :datasets="datasets"
                    :collections="collections"
                    :histories="histories"
                    :invocations="invocations"
                    :time="time"
                    :version="version"
                    :workflows="workflows" />
            </div>
        </div>
    </div>
</template>
