<template>
    <div>
        <div class="donemessagelarge">
            <p>
                Successfully invoked workflow <b>{{ workflowName }}</b>
                <em v-if="multipleInvocations"> - {{ timesExecuted }} times</em>.
            </p>

            <p v-if="multipleHistoryTargets">
                This workflow will generate results in multiple histories. You can observe progress in the
                <a :href="multiHistoryView">history multi-view</a>.
            </p>
            <p v-else-if="wasNewHistoryTarget">
                This workflow will generate results in a new history.
                <a class="workflow-new-history-target-link" :href="newHistoryTarget">Switch to that history now</a>.
            </p>
            <p v-else>You can check the status of queued jobs and view the resulting data the History panel.</p>
        </div>
        <workflow-invocation-state
            v-for="(invocation, index) in invocations"
            :key="invocation.id"
            :index="index"
            :invocation-id="invocation.id" />
        <div id="webhook-view"></div>
    </div>
</template>

<script>
import { mapGetters } from "vuex";
import WorkflowInvocationState from "components/WorkflowInvocationState/WorkflowInvocationState";
import Webhooks from "utils/webhooks";
import { getAppRoot } from "onload/loadConfig";
import { refreshContentsWrapper } from "utils/data";

export default {
    components: {
        WorkflowInvocationState,
    },
    props: {
        workflowName: {
            type: String,
            required: true,
        },
        invocations: {
            type: Array,
            required: true,
        },
    },
    computed: {
        ...mapGetters("history", ["currentHistoryId"]),
        timesExecuted() {
            return this.invocations.length;
        },
        multipleInvocations() {
            return this.timesExecuted > 1;
        },
        multipleHistoryTargets() {
            return this.targetHistories.length > 1;
        },
        targetHistories() {
            return this.invocations.reduce((histories, invocation) => {
                if (invocation.history_id && !histories.includes(invocation.history_id)) {
                    histories.push(invocation.history_id);
                }
                return histories;
            }, []);
        },
        multiHistoryView() {
            return `${getAppRoot()}histories/view_multiple`;
        },
        newHistoryTarget() {
            return `${getAppRoot()}history/switch_to_history?hist_id=${this.invocations[0].history_id}`;
        },
        wasNewHistoryTarget() {
            if (this.invocations.length < 1) {
                return false;
            }
            return this.invocations[0].history_id && this.currentHistoryId != this.invocations[0].history_id;
        },
    },
    mounted() {
        new Webhooks.WebhookView({
            type: "workflow",
            toolId: null,
            toolVersion: null,
        });
        refreshContentsWrapper();
    },
};
</script>
