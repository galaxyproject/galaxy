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
                        <!-- set provideContext to false, since the table itself provides this information -->
                        <workflow-invocation-state :invocation-id="row.item.id" :provide-context="false" />
                    </b-card>
                </template>
                <template v-slot:cell(details)="data">
                    <b-button
                        v-b-tooltip.hover.bottom
                        title="Show Invocation Details"
                        class="btn-sm fa fa-chevron-down"
                        v-if="!data.detailsShowing"
                        @click.stop="swapRowDetails(data)"
                    />
                    <b-button
                        v-b-tooltip.hover.bottom
                        title="Hide Invocation Details"
                        class="btn-sm fa fa-chevron-up"
                        v-if="data.detailsShowing"
                        @click.stop="swapRowDetails(data)"
                    />
                </template>
                <template v-slot:cell(workflow_id)="data">
                    <div v-if="!ownerGrid || !getWorkflowByInstanceId(data.item.workflow_id)">
                        {{ data.item.workflow_id }}
                    </div>
                    <div v-else>
                        <workflow-dropdown :workflow="getWorkflowByInstanceId(data.item.workflow_id)" />
                    </div>
                </template>
                <template v-slot:cell(history_id)="data">
                    <div v-if="!ownerGrid || !getHistoryById(data.item.history_id)">
                        {{ data.item.history_id }}
                    </div>
                    <div v-else>
                        <history-dropdown :history="getHistoryById(data.item.history_id)" />
                    </div>
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import { getRootFromIndexLink } from "onload";
import { WorkflowInvocationState } from "components/WorkflowInvocationState";
import LoadingSpan from "components/LoadingSpan";
import WorkflowDropdown from "components/Workflow/WorkflowDropdown";
import HistoryDropdown from "components/History/HistoryDropdown";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

export default {
    components: {
        WorkflowInvocationState,
        LoadingSpan,
        WorkflowDropdown,
        HistoryDropdown,
    },
    props: {
        invocationItems: { type: Array, default: () => [] },
        loading: { type: Boolean, default: true },
        noInvocationsMessage: { type: String },
        headerMessage: { type: String, default: "" },
        ownerGrid: { type: Boolean, default: true },
    },
    data() {
        const fields = [
            { key: "details", label: "" },
            { key: "workflow_id", label: "Workflow" },
            { key: "history_id", label: "History" },
            { key: "id", label: "Invocation ID" },
            { key: "state" },
            { key: "update_time", label: "Last Update" },
            { key: "create_time", label: "Invocation Time" },
        ];
        return {
            invocationItemsModel: [],
            invocationFields: fields,
            status: "",
        };
    },
    computed: {
        ...mapGetters(["getWorkflowByInstanceId", "getHistoryById"]),
        invocationItemsComputed() {
            return this.computeItems(this.invocationItems);
        },
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId", "fetchHistoryForId"]),
        editLink(workflowId) {
            return getRootFromIndexLink() + "workflow/editor?id=" + this.getWorkflowByInstanceId(workflowId).id;
        },
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
    },
};
</script>
