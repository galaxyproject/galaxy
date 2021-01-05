<template>
    <div v-if="invocation">
        <div v-if="Object.keys(invocation.input_step_parameters).length">
            <details
                ><summary><b>Parameters</b></summary>
                <parameter-step :parameters="Object.values(invocation.input_step_parameters)" />
            </details>
        </div>
        <div v-if="Object.keys(invocation.inputs).length">
            <details
                ><summary><b>Inputs</b></summary>
                <div v-for="(input, key) in invocation.inputs" :key="input.id">
                    <b>{{ dataInputStepLabel(key, input) }}</b>
                    <workflow-invocation-data-contents :data_item="input" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.outputs).length">
            <details
                ><summary><b>Outputs</b></summary>
                <div v-for="(output, key) in invocation.outputs" :key="output.id">
                    <b>{{ key }}:</b>
                    <workflow-invocation-data-contents :data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.output_collections).length">
            <details
                ><summary><b>Output Collections</b></summary>
                <div v-for="(output, key) in invocation.output_collections" :key="output.id">
                    <b>{{ key }}:</b>
                    <workflow-invocation-data-contents :data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="workflow">
            <details v-if="workflow"
                ><summary><b>Steps</b></summary>
                <workflow-invocation-step
                    v-for="step in Object.values(workflow.steps)"
                    :invocation="invocation"
                    :orderedSteps="orderedSteps"
                    :key="step.id"
                    :workflow="workflow"
                    :workflowStep="step"
                />
            </details>
        </div>
    </div>
</template>
<script>
import ParameterStep from "./ParameterStep.vue";
import WorkflowInvocationDataContents from "./WorkflowInvocationDataContents";
import WorkflowInvocationStep from "./WorkflowInvocationStep";
import ListMixin from "components/History/ListMixin";
import { getHistoryMonitor } from "./providers/monitors";

import { mapGetters } from "vuex";
import { mapCacheActions } from "vuex-cache";
import { filter, takeUntil } from "rxjs/operators";
import { vueRxShortcuts } from "components/plugins";

export default {
    mixins: [ListMixin, vueRxShortcuts],
    components: {
        WorkflowInvocationDataContents,
        WorkflowInvocationStep,
        ParameterStep,
    },
    props: {
        invocation: {
            required: true,
        },
        jobStatesTerminal: {
            required: true,
            type: Boolean,
        },
    },
    created: function () {
        this.fetchWorkflowForInstanceId(this.invocation.workflow_id);
        this.monitorHistory();
    },
    computed: {
        ...mapGetters(["getWorkflowByInstanceId"]),
        orderedSteps() {
            return [...this.invocation.steps].sort((a, b) => a.order_index - b.order_index);
        },
        workflow() {
            return this.getWorkflowByInstanceId(this.invocation.workflow_id);
        },
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId"]),
        dataInputStepLabel(key, input) {
            const invocationStep = this.orderedSteps[key];
            let label = invocationStep && invocationStep.workflow_step_label;
            if (!label) {
                if (input.src === "hda" || input.src === "ldda") {
                    label = "Input dataset";
                } else if (input.src === "hdca") {
                    label = "Input dataset collection";
                }
            }
            return label;
        },
        monitorHistory() {
            // rework this into history or invocation subscription in the future ...
            if (!this.jobStatesTerminal) {
                const pollHistory$ = this.watch$("jobStatesTerminal");
                const stopPolling$ = pollHistory$.pipe(filter((val) => val === true));
                const historyMonitor$ = getHistoryMonitor(this.invocation.history_id).pipe(takeUntil(stopPolling$));
                this.listenTo(historyMonitor$, {
                    error: (err) => console.error("An error occured while monitoring history for datasets", err),
                    complete: () => console.log("Invocation finished, stopping history dataset monitor"),
                });
            }
        },
    },
};
</script>
