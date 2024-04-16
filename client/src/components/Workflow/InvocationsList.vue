<template>
    <div class="invocations-list" aria-labelledby="invocations-title">
        <div class="grid-header d-flex justify-content-between pb-2 flex-column">
            <div class="d-flex">
                <Heading h1 separator inline size="xl" class="flex-grow-1 m-0" data-description="grid title">
                    <span v-localize>{{ title }}</span>
                </Heading>
            </div>
        </div>
        <b-alert v-if="headerMessage" variant="info" show>
            {{ headerMessage }}
        </b-alert>
        <b-alert v-bind="alertAttrs">{{ message }}</b-alert>
        <b-table
            v-bind="indexTableAttrs"
            v-model="invocationItemsModel"
            no-sort-reset
            :fields="invocationFields"
            class="invocations-table">
            <template v-slot:empty>
                <loading-span v-if="loading" message="Loading workflow invocations" />
                <b-alert v-else id="no-invocations" variant="info" show>
                    {{ effectiveNoInvocationsMessage }}
                </b-alert>
            </template>
            <template v-slot:row-details="row">
                <b-card>
                    <small class="float-right" :data-invocation-id="row.item.id">
                        <b>Last updated: <UtcDate :date="row.item.update_time" mode="elapsed" />;</b>
                        <b
                            >Invocation ID:
                            <router-link :to="invocationLink(row.item)">{{ row.item.id }}</router-link></b
                        >
                    </small>
                    <WorkflowInvocationState :invocation-id="row.item.id" @invocation-cancelled="refresh" />
                </b-card>
            </template>
            <template v-slot:cell(expand)="data">
                <b-link
                    v-if="!data.detailsShowing"
                    v-b-tooltip.hover.top
                    title="Show Details"
                    class="btn-sm fa fa-lg fa-chevron-down toggle-invocation-details"
                    @click.stop="swapRowDetails(data)" />
                <b-link
                    v-if="data.detailsShowing"
                    v-b-tooltip.hover.top
                    title="Hide Details"
                    class="btn-sm fa fa-lg fa-chevron-up toggle-invocation-details"
                    @click.stop="swapRowDetails(data)" />
            </template>
            <template v-slot:cell(workflow_id)="data">
                <div class="truncate">
                    <router-link
                        v-b-tooltip.hover.top
                        :title="`Go to detailed view for '${getStoredWorkflowNameByInstanceId(data.item.workflow_id)}'`"
                        :to="invocationLink(data.item)">
                        {{ getStoredWorkflowNameByInstanceId(data.item.workflow_id) }}
                    </router-link>
                </div>
            </template>
            <template v-slot:cell(history_id)="data">
                <SwitchToHistoryLink :history-id="data.value" />
            </template>
            <template v-slot:cell(create_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
            <template v-slot:cell(update_time)="data">
                <UtcDate :date="data.value" mode="elapsed" />
            </template>
            <template v-slot:cell(state)="data">
                <HelpText :uri="`galaxy.invocations.states.${data.value}`" :text="data.value" />
            </template>
            <template v-slot:cell(execute)="data">
                <WorkflowRunButton
                    v-if="getStoredWorkflowIdByInstanceId(data.item.workflow_id)"
                    :id="getStoredWorkflowIdByInstanceId(data.item.workflow_id)"
                    :root="root" />
            </template>
        </b-table>
        <b-pagination
            v-if="rows >= perPage"
            v-model="currentPage"
            class="gx-invocations-grid-pager"
            v-bind="paginationAttrs"></b-pagination>
    </div>
</template>

<script>
import HelpText from "components/Help/HelpText";
import { invocationsProvider } from "components/providers/InvocationsProvider";
import UtcDate from "components/UtcDate";
import WorkflowInvocationState from "components/WorkflowInvocationState/WorkflowInvocationState";
import { mapActions, mapState } from "pinia";

import { useHistoryStore } from "@/stores/historyStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import paginationMixin from "./paginationMixin";

import Heading from "../Common/Heading.vue";
import WorkflowRunButton from "./WorkflowRunButton.vue";
import SwitchToHistoryLink from "@/components/History/SwitchToHistoryLink.vue";

export default {
    components: {
        Heading,
        HelpText,
        UtcDate,
        WorkflowInvocationState,
        WorkflowRunButton,
        SwitchToHistoryLink,
    },
    mixins: [paginationMixin],
    props: {
        noInvocationsMessage: { type: String, default: "No Workflow Invocations to display" },
        headerMessage: { type: String, default: "" },
        ownerGrid: { type: Boolean, default: true },
        userId: { type: String, default: null },
        historyId: { type: String, default: null },
        historyName: { type: String, default: null },
        storedWorkflowId: { type: String, default: null },
        storedWorkflowName: { type: String, default: null },
    },
    data() {
        const fields = [{ key: "expand", label: "", class: "col-button" }];
        if (!this.storedWorkflowId) {
            fields.push({ key: "workflow_id", label: "Workflow", class: "col-name" });
        }
        if (!this.historyId) {
            fields.push({ key: "history_id", label: "History", class: "col-history" });
        }
        fields.push(
            { key: "create_time", label: "Invoked", class: "col-small", sortable: true },
            { key: "state", class: "col-small" },
            { key: "execute", label: "Run", class: "col-button" }
        );
        return {
            tableId: "invocation-list-table",
            dataProvider: invocationsProvider,
            invocationItemsModel: [],
            invocationFields: fields,
            perPage: this.rowsPerPage(this.defaultPerPage || 50),
        };
    },
    computed: {
        ...mapState(useWorkflowStore, [
            "getStoredWorkflowByInstanceId",
            "getStoredWorkflowIdByInstanceId",
            "getStoredWorkflowNameByInstanceId",
        ]),
        ...mapState(useHistoryStore, ["getHistoryById", "getHistoryNameById"]),
        title() {
            let title = `Workflow Invocations`;
            if (this.storedWorkflowName) {
                title += ` for workflow "${this.storedWorkflowName}"`;
            }
            if (this.historyName) {
                title += ` for history "${this.historyName}"`;
            }
            return title;
        },
        effectiveNoInvocationsMessage() {
            let message = this.noInvocationsMessage;
            if (this.storedWorkflowName) {
                message += ` for ${this.storedWorkflowName}`;
            }
            if (this.historyName) {
                message += ` for ${this.historyName}`;
            }
            return message;
        },
        dataProviderParameters() {
            const extraParams = this.ownerGrid ? {} : { include_terminal: false };
            if (this.storedWorkflowId) {
                extraParams["workflow_id"] = this.storedWorkflowId;
            } else {
                extraParams["include_nested_invocations"] = false;
            }
            if (this.historyId) {
                extraParams["history_id"] = this.historyId;
            }
            if (this.userId) {
                extraParams["user_id"] = this.userId;
            }
            return extraParams;
        },
    },
    watch: {
        items: function (invocations) {
            if (invocations) {
                const historyIds = new Set();
                const workflowIds = new Set();
                invocations.forEach((invocation) => {
                    historyIds.add(invocation.history_id);
                    workflowIds.add(invocation.workflow_id);
                });
                historyIds.forEach((history_id) => this.getHistoryById(history_id) || this.loadHistoryById(history_id));
                workflowIds.forEach((workflow_id) => this.fetchWorkflowForInstanceIdCached(workflow_id));
            }
        },
    },
    methods: {
        ...mapActions(useHistoryStore, ["loadHistoryById"]),
        ...mapActions(useWorkflowStore, ["fetchWorkflowForInstanceIdCached"]),
        swapRowDetails(row) {
            row.toggleDetails();
        },
        invocationLink(item) {
            return `/workflows/invocations/${item.id}`;
        },
    },
};
</script>
<style scoped>
.invocations-table {
    min-width: 40rem;
}

.table:deep(.col-name) {
    width: 40%;
}

.table:deep(.col-history) {
    width: 20%;
}

.table:deep(.col-small) {
    width: 100px;
}

.table:deep(.col-button) {
    width: 50px;
}

.table:deep(.truncate) {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
</style>
