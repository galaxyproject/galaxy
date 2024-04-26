<template>
    <div>
        <div class="donemessagelarge">
            <p>
                Successfully invoked workflow <b>{{ workflowName }}</b>
                <em v-if="multipleInvocations"> - {{ timesExecuted }} times</em>.
            </p>

            <p v-if="multipleHistoryTargets">
                This workflow will generate results in multiple histories. You can observe progress in the
                <router-link to="/histories/view_multiple">history multi-view</router-link>.
            </p>
            <p v-else-if="wasNewHistoryTarget">
                This workflow will generate results in a new history.
                <a class="workflow-new-history-target-link" href="javascript:void(0)" @click="switchHistory"
                    >Switch to that history now</a
                >.
            </p>
            <p v-else>You can check the status of queued jobs and view the resulting data the History panel.</p>
            <p>
                View all of your workflow invocations in the
                <router-link to="/workflows/invocations">Invocations List</router-link>.
            </p>
        </div>
        <WorkflowInvocationState
            v-for="(invocation, index) in invocations"
            :key="invocation.id"
            :index="index"
            :invocation-id="invocation.id"
            full-page />
        <div id="webhook-view"></div>
    </div>
</template>

<script>
import WorkflowInvocationState from "components/WorkflowInvocationState/WorkflowInvocationState";
import { getAppRoot } from "onload/loadConfig";
import { mapActions, mapState } from "pinia";
import { refreshContentsWrapper } from "utils/data";
import Webhooks from "utils/webhooks";

import { useHistoryStore } from "@/stores/historyStore";

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
        ...mapState(useHistoryStore, ["currentHistoryId"]),
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
    methods: {
        ...mapActions(useHistoryStore, ["setCurrentHistory"]),
        async switchHistory() {
            await this.setCurrentHistory(this.invocations[0].history_id);
        },
    },
};
</script>
