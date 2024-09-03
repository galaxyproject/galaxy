<template>
    <div>
        <b>Workflow: {{ model.name }}</b> <i>(version: {{ model.runData.version + 1 }})</i>

        <FontAwesomeIcon icon="chevron-up" class="fa-fw" />

        <FontAwesomeIcon 
            :icon="computedExpanded ? 'chevron-up' : 'chevron-down'" 
            :title="computedExpanded ? 'show' : 'hide'"
            @click="computedExpanded = !computedExpanded" />

        <WorkflowInformation
            v-if="this.workflowInfoData"
            class="workflow-information-container"
            :workflow-info="this.workflowInfoData"
            :embedded="false" />
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
        canMutateCurrentHistory: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
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
