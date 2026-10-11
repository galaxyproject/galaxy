<template>
    <div>
        <ToolForm v-if="isTool && !isUpload" v-bind="toolParams" />
        <WorkflowRun v-else-if="isWorkflow" v-bind="workflowParams" />
        <div v-else-if="isController" :src="controllerParams" />
        <CenterFrame v-else src="/welcome" />
    </div>
</template>

<script setup lang="ts">
import decodeUriComponent from "decode-uri-component";
import { computed, nextTick, onMounted } from "vue";
import { type LocationQuery, useRoute, useRouter } from "vue-router";

import { useToast } from "@/composables/toast";

import ToolForm from "@/components/Tool/ToolForm.vue";
import WorkflowRun from "@/components/Workflow/Run/WorkflowRun.vue";
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

interface HomeConfig {
    simplified_workflow_run_ui?: string;
    simplified_workflow_run_ui_target_history?: string;
    simplified_workflow_run_ui_job_cache?: string;
}

const props = defineProps<{
    config: HomeConfig;
    query: LocationQuery;
}>();

const route = useRoute();
const router = useRouter();
const toast = useToast();

// A repeated or valueless query param can't name a tool or workflow, so only plain strings count.
function queryValue(key: string): string | undefined {
    const value = props.query[key];
    return typeof value === "string" ? value : undefined;
}

function decodeUnlessPlus(value: string): string {
    return value.indexOf("+") >= 0 ? value : decodeUriComponent(value);
}

const isController = computed(() => queryValue("m_c") && queryValue("m_a"));
const isTool = computed(() => queryValue("tool_id") || queryValue("tool_uuid") || queryValue("job_id"));
const isUpload = computed(() => queryValue("tool_id") === "upload1");
const isWorkflow = computed(() => queryValue("workflow_id"));
const controllerParams = computed(() => `${queryValue("m_c")}/${queryValue("m_a")}`);

const toolParams = computed(() => {
    const result: { uuid?: string; jobId?: string; id?: string; version?: string } = {
        uuid: queryValue("tool_uuid"),
        jobId: queryValue("job_id"),
    };
    const toolId = queryValue("tool_id");
    if (toolId) {
        result.id = decodeUnlessPlus(toolId);
    }
    const toolVersion = queryValue("version");
    if (toolVersion) {
        result.version = decodeUnlessPlus(toolVersion);
    }
    return result;
});

const workflowParams = computed(() => {
    const preferSimpleForm =
        props.config.simplified_workflow_run_ui == "prefer" || queryValue("simplified_workflow_run_ui") == "prefer";
    return {
        workflowId: queryValue("workflow_id") ?? "",
        version: queryValue("version"),
        preferSimpleForm,
        simpleFormTargetHistory: props.config.simplified_workflow_run_ui_target_history,
        simpleFormUseJobCache: props.config.simplified_workflow_run_ui_job_cache == "on",
    };
});

onMounted(() => {
    // Data source tools redirect back to the SPA after a server-side
    // import; surface a toast and strip the param so a reload doesn't
    // re-fire it.
    if (props.query.notification === "tool-submitted") {
        nextTick(() => {
            toast.addToast("Check your history panel for progress.", {
                title: "Data import queued",
                variant: "info",
                duration: 0,
            });
        });
        const newQuery = { ...route.query };
        delete newQuery.notification;
        router.replace({ query: newQuery });
    }
});
</script>
