<template>
    <div>
        <h2 class="mb-3">
            <span id="invocations-title">Workflow Invocations</span>
        </h2>
        <b-alert variant="info" show v-if="headerMessage">
            {{ headerMessage }}
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            <loading-span message="Loading workflow invocation job data" />
        </b-alert>
        <div v-else>
            <b-alert v-if="!invocationItemsComputed.length" variant="secondary" show>
                {{ noInvocationsMessage }}
            </b-alert>
            <b-table
                v-else
                :fields="invocationFields"
                :items="invocationItemsComputed"
                v-model="invocationItemsModel"
                hover
                striped
                caption-top
                :busy="loading"
            >
                <template v-slot:table-caption>
                    These invocations are not finished scheduling - one or more steps are waiting on others steps to be
                    complete before the full structure of the jobs in the workflow can be determined.
                </template>
                <template v-slot:row-details="row">
                    <b-card>
                        <workflow-invocation-state :invocation-id="row.item.id" />
                    </b-card>
                </template>
                <template v-slot:cell(workflow_id)="data">
                    <b-link href="#" @click.stop="swapRowDetails(data)">
                        <b>{{ getWorkflowNameByInstanceId(data.item.workflow_id) }}</b>
                    </b-link>
                </template>
                <template v-slot:cell(history_id)="data">
                    {{ getHistoryNameById(data.item.history_id) }}
                </template>
                <template v-slot:cell(create_time)="data">
                    <UtcDate :date="data.value" mode="elapsed" />
                </template>
                <template v-slot:cell(execute)="data">
                    <b-button
                        v-b-tooltip.hover.bottom
                        title="Rerun Workflow"
                        class="workflow-run btn-sm btn-primary fa fa-play"
                        @click.stop="executeWorkflow(getWorkflowByInstanceId(data.item.workflow_id).id)"
                    />
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { WorkflowInvocationState } from "components/WorkflowInvocationState";
import UtcDate from "components/UtcDate";
import LoadingSpan from "components/LoadingSpan";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

export default {
    components: {
        UtcDate,
        WorkflowInvocationState,
        LoadingSpan,
    },
    props: {
        invocationItems: { type: Array, default: () => [] },
        loading: { type: Boolean, default: true },
        noInvocationsMessage: { type: String, default: "" },
        headerMessage: { type: String, default: "" },
        ownerGrid: { type: Boolean, default: true },
    },
    data() {
        const fields = [
            { key: "workflow_id", label: "Workflow" },
            { key: "history_id", label: "History" },
            { key: "create_time", label: "Invoked" },
            { key: "state" },
            { key: "execute", label: "" },
        ];
        return {
            invocationItemsModel: [],
            invocationFields: fields,
            status: "",
        };
    },
    computed: {
        ...mapGetters(["getWorkflowNameByInstanceId", "getWorkflowByInstanceId", "getHistoryNameById"]),
        invocationItemsComputed() {
            return this.computeItems(this.invocationItems);
        },
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId", "fetchHistoryForId"]),
        computeItems(items) {
            return items.map((invocation) => {
                if (this.ownerGrid) {
                    this.fetchWorkflowForInstanceId(invocation["workflow_id"]);
                    this.fetchHistoryForId(invocation["history_id"]);
                }
                return {
                    id: invocation["id"],
                    create_time: invocation["create_time"],
                    update_time: invocation["update_time"],
                    workflow_id: invocation["workflow_id"],
                    history_id: invocation["history_id"],
                    state: invocation["state"],
                    _showDetails: false,
                };
            });
        },
        swapRowDetails(row) {
            row.toggleDetails();
        },
        handleError(error) {
            console.error(error);
        },
        executeWorkflow: function (workflow_id) {
            window.location = `${getAppRoot()}workflows/run?id=${workflow_id}`;
        },
    },
};
</script>
