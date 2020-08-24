<template>
    <div>
        <div class="ui-portlet-section">
            <div class="portlet-header portlet-title portlet-operations" v-on:click="toggleStep">
                <i class="'portlet-title-icon fa mr-1 ' + stepIcon" style="display: inline;"></i>
                <span class="portlet-title-text no-highlight collapsible">
                    {{stepLabel}}
                </span>
            </div>
            <div class="portlet-content" v-show="expanded">
                <div class="portlet-body">
                    {{ step }}
                    <p></p>
                    Workflow:
                    <p>{{workflow}}</p>
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex"
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        step: Object,
        workflow: Object,
    },
    data() {
        return {
            expanded: false,
        };
    },
    mounted() {
        this.fetchTools();
    },
    computed: {
        ...mapGetters(["getToolForId", "getToolNameById", "getWorkflowByInstanceId"]),
        workflowStepType() {
            return this.workflow.steps[this.step.order_index];
        },
        stepIcon() {
            switch (this.workflowStepType) {
                case "data_input":
                    return 'fa-file';
                case "data_collection_input":
                    return 'fa-folder-o';
                case "pencil-square":
                    return 'pencil-square';
                default:
                    return 'fa-wrench';
            }
        },
        stepLabel() {
            const stepIndex = this.step.order_index + 1;
            if (this.step.workflow_step_label) {
                return `Step ${stepIndex}: ${this.step.workflow_step_label}`;
            }
            const workflowStep = this.workflow.steps[this.step.order_index]
            const workflowStepType = workflowStep.type;
            switch (workflowStepType) {
                case "tool":
                    return this.toolStepLabel(workflowStep);
                case "subworkflow":
                    return this.subWorkflowStepLabel(workflowStep);
                case "parameter_input":
                    return `Step ${stepIndex}: Parameter input`;
                case "data_input":
                    `Step ${stepIndex}: Data input`
                case "data_collection_input":
                    return `Step ${stepIndex}: Data collection input`
                default:
                    return `Step ${stepIndex}: Unknown step type '${workflowStepType}'`;
            }
        },
    },
    methods: {
        ...mapCacheActions(["fetchToolForId"]),
        fetchTools() {
            Object.values(this.workflow.steps).map((step) => {
                if (step.tool_id && !this.getToolForId(step.tool_id)) {
                    this.fetchToolForId(step.tool_id)
                }
            })
        },
        toggleStep() {
            this.expanded = !this.expanded;
        },
        toolStepLabel(workflowStep) {
            const name = this.getToolNameById(workflowStep.tool_id);
            return `Step ${this.step.order_index +1}: ${name}`;
        },
        subWorkflowStepLabel(workflowStep) {
            const subworkflow = this.getWorkflowByInstanceId(workflowStep.workflow_id)
            return `Step ${this.step.order_index + 1}: ${subworkflow.name}`
        },
    },    
}
</script>