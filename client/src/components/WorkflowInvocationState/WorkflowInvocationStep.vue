<template>
    <div class="d-flex">
        <div class="ui-portlet-section" style="width: 100%">
            <div class="portlet-header portlet-title portlet-operations" v-on:click="toggleStep">
                <i :class="'portlet-title-icon fa mr-1 ' + stepIcon"></i>
                <span class="portlet-title-text">
                    <u>{{stepLabel}}</u>
                </span>
            </div>
            <div class="portlet-content" v-show="expanded">
                <div style="min-width: 1;"/>
                <div class="portlet-body" style="width: 100%; overflow-x: auto;">
                    <b-table small caption-top :items="stepDetails.jobs" :fields="jobFields" v-if="stepDetails" @row-clicked="item=>$set(item, '_showDetails', !item._showDetails)">
                        <template v-slot:row-details="row">
                                <job-provider
                                    :id="row.item.id"
                                    v-slot="{
                                        item,
                                        loading,
                                    }">
                                    <job-details :job="item" v-if="item"/>
                                </job-provider>
                        </template>
                        <template v-slot:cell(create_time)="data">
                            <UtcDate :date="data.value" mode="elapsed" />
                        </template>
                        <template v-slot:cell(update_time)="data">
                            <UtcDate :date="data.value" mode="elapsed" />
                        </template>
                    </b-table>
                </div>
                <div style="min-width: 1;"/>
            </div>
        </div>
    </div>
</template>
<script>
import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex"
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { JobProvider } from "components/History/providers/DatasetProvider"
import JobDetails from "components/admin/JobDetails"
import UtcDate from "components/UtcDate";

Vue.use(BootstrapVue);

export default {
    components: {
        UtcDate,
        JobProvider,
        JobDetails,
    },
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
        this.fetchTool();
        this.fetchInvocationStepById(this.step.id)
    },
    computed: {
        ...mapGetters(["getToolForId", "getToolNameById", "getWorkflowByInstanceId", "getInvocationStepById"]),
        workflowStep() {
            return this.workflow.steps[this.step.order_index];
        },
        workflowStepType() {
            return this.workflowStep.type;
        },
        stepIcon() {
            console.log(this.workflowStepType);
            switch (this.workflowStepType) {
                case "data_input":
                    return 'fa-file';
                case "data_collection_input":
                    return 'fa-folder-o';
                case "parameter_input":
                    return 'fa-pencil';
                default:
                    return 'fa-wrench';
            }
        },
        jobFields() {
            return [
                'state',
                'exit_code',
                {key: 'update_time', label: 'Updated'},
                {key: 'create_time', label: 'Created'},
            ]
        },
        stepDetails() {
            return this.getInvocationStepById(this.step.id)
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
        ...mapCacheActions(["fetchToolForId", "fetchInvocationStepById"]),
        fetchTool() {
            if (this.workflowStep.tool_id && !this.getToolForId(this.workflowStep.tool_id)) {
                    this.fetchToolForId(this.workflowStep.tool_id)
                }
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