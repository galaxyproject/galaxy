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
                responsive
                striped
                caption-top
                @row-clicked="showRowDetails"
                :busy="busy"
            >
                <template v-slot:table-caption>
                    These invocations are not finished scheduling - one or more steps are waiting on others steps to be
                    complete before the full structure of the jobs in the workflow can be determined.
                </template>
                <template v-slot:row-details="row">
                    <b-card>
                        <!-- set provideContext to false, since the table itself provides this information -->
                        <workflow-invocation-state :invocationId="row.item.id" :provideContext="false" />
                    </b-card>
                </template>
            </b-table>
        </div>
    </div>
</template>

<script>
import { WorkflowInvocationState } from "components/WorkflowInvocationState";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        WorkflowInvocationState,
        LoadingSpan
    },
    props: {
        invocationItems: { type: Array, default: [] },
        busy: { type: Boolean, default: true },
        loading: { type: Boolean, default: true },
        noInvocationsMessage: { type: String },
        headerMessage: { type: String, default: '' }
    },
    data() {
        return {
            invocationItemsModel: [],
            invocationFields: [
                { key: "id", label: "Invocation ID", sortable: true },
                // { key: "user" },
                { key: "state" },
                { key: "update_time", label: "Last Update", sortable: true },
                { key: "create_time", label: "Invocation Time", sortable: true }
            ],
            status: "",
        };
    },
    computed: {
        invocationItemsComputed() {
            return this.computeItems(this.invocationItems);
        }
    },
    methods: {
        computeItems(items) {
            return items.map(invocation => {
                return {
                    id: invocation["id"],
                    create_time: invocation["create_time"],
                    update_time: invocation["update_time"],
                    state: invocation["state"],
                    _showDetails: false
                };
            });
        },
        showRowDetails(row, index, e) {
            if (e.target.nodeName != "A") {
                row._showDetails = !row._showDetails;
            }
        },
        handleError(error) {
            console.error(error);
        }
    }
};
</script>
