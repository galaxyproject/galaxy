<template>
    <div>
        <ToolForm v-if="isTool && !isUpload" v-bind="toolParams" />
        <WorkflowRun v-else-if="isWorkflow" v-bind="workflowParams" />
        <div v-else-if="isController" :src="controllerParams" />
        <CenterFrame v-else src="/welcome" />
    </div>
</template>

<script>
import ToolForm from "components/Tool/ToolForm";
import WorkflowRun from "components/Workflow/Run/WorkflowRun";
import decodeUriComponent from "decode-uri-component";
import CenterFrame from "entry/analysis/modules/CenterFrame";

export default {
    components: {
        CenterFrame,
        ToolForm,
        WorkflowRun,
    },
    props: {
        config: {
            type: Object,
            required: true,
        },
        query: {
            type: Object,
            required: true,
        },
    },
    computed: {
        isController() {
            return this.query.m_c && this.query.m_a;
        },
        isTool() {
            return this.query.tool_id || this.query.tool_uuid || this.query.job_id;
        },
        isUpload() {
            return this.query.tool_id === "upload1";
        },
        isWorkflow() {
            return this.query.workflow_id;
        },
        controllerParams() {
            return `${this.query.m_c}/${this.query.m_a}`;
        },
        toolParams() {
            const result = { ...this.query };
            result.uuid = this.query.tool_uuid;
            const tool_id = this.query.tool_id;
            if (tool_id) {
                result.id = tool_id.indexOf("+") >= 0 ? tool_id : decodeUriComponent(tool_id);
            }
            const tool_version = this.query.version;
            if (tool_version) {
                result.version = tool_version.indexOf("+") >= 0 ? tool_version : decodeUriComponent(tool_version);
            }
            return result;
        },
        workflowParams() {
            const workflowId = this.query.workflow_id;
            const version = this.query.version;
            let preferSimpleForm = this.config.simplified_workflow_run_ui == "prefer";
            const preferSimpleFormOverride = this.query.simplified_workflow_run_ui;
            if (preferSimpleFormOverride == "prefer") {
                preferSimpleForm = true;
            }
            const simpleFormTargetHistory = this.config.simplified_workflow_run_ui_target_history;
            const simpleFormUseJobCache = this.config.simplified_workflow_run_ui_job_cache == "on";
            return {
                workflowId,
                version,
                preferSimpleForm,
                simpleFormTargetHistory,
                simpleFormUseJobCache,
            };
        },
    },
};
</script>
