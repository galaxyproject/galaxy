<template>
    <div>
        <b>Workflow: {{ model.name }}</b> <i>(version: {{ model.runData.version + 1 }})</i>
        <div v-if="this.workflowInfoData" class="ui-portlet-section w-100">
            <div
                class="portlet-header portlet-operations"
                role="button"
                tabindex="0"
                @keyup.enter="expandAnnotations = !expandAnnotations"
                @click="expandAnnotations = !expandAnnotations">
                <span class="portlet-title-text">
                    <u v-localize class="step-title ml-2">About This Workflow</u>
                </span>
                <FontAwesomeIcon class="float-right" :icon="expandAnnotations ? 'chevron-up' : 'chevron-down'" />
            </div>
            <div class="portlet-content" :style="expandAnnotations ? 'display: none;' : ''">
                <WorkflowInformation
                    v-if="this.workflowInfoData"
                    class="workflow-information-container"
                    :workflow-info="this.workflowInfoData"
                    :embedded="false" />
            </div>
        </div>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getWorkflowFull, getWorkflowInfo } from "@/components/Workflow/workflows.services";
import WorkflowInformation from "@/components/Workflow/Published/WorkflowInformation.vue";

export default {
    components: {
        WorkflowInformation,
        FontAwesomeIcon,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            expandAnnotations: true,
            workflowInfoData: {},
            fullWorkflow: {},
        };
    },
    computed: {
        workflowInfo() {
            return this.model.runData;
        },
    },
    mounted() {
        this.loadAnnotation();
    },
    methods: {
        async loadAnnotation() { //TODO code cleanup
            // errorMessage.value = "";

            try {
                const workflowInfoDataPromise = getWorkflowInfo(this.model.runData.id);
                const fullWorkflowPromise = getWorkflowFull(this.model.runData.id);
                this.workflowInfoData = await workflowInfoDataPromise;
                this.fullWorkflow = await fullWorkflowPromise;

                // assertDefined(workflowInfoData.name);
                // this.workflowInfo = workflowInfoData;
                // this.workflow = fullWorkflow;

                // fromSimple(model.runData.id, fullWorkflow);
            } catch (e) {
                const error = e;

                // if (error.response?.data.err_msg) {
                //     this.errorMessage.value = error.response.data.err_msg ?? "Unknown Error";
                // }
            } finally {
                // this.loading.value = false;
            }
        },
    },
};
</script>
