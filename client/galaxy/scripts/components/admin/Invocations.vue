<template>
    <div>
        <h2 class="mb-3">
            <span id="invocations-title">Workflow Invocations</span>
        </h2>
        <b-alert variant="info" show>
            <p>
                Workflow invocations that are still being scheduled are displayed on this page.
            </p>
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            <loading-span message="Loading workflow invocation job data" />
        </b-alert>
        <div v-else>
            <b-alert v-if="!invocationItemsComputed.length" variant="secondary" show>
                There are no scheduling workflow invocations to show currently.
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
import { getActiveInvocations } from "./AdminServices";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        WorkflowInvocationState,
        LoadingSpan
    },
    data() {
        return {
            invocationItems: [],
            invocationItemsModel: [],
            invocationFields: [
                { key: "id", label: "Invocation ID", sortable: true },
                // { key: "user" },
                { key: "state" },
                { key: "update_time", label: "Last Update", sortable: true },
                { key: "create_time", label: "Invocation Time", sortable: true }
            ],
            status: "",
            loading: true,
            busy: true
        };
    },
    computed: {
        invocationItemsComputed() {
            return this.computeItems(this.invocationItems);
        }
    },
    created() {
        this.update();
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
        update() {
            this.busy = true;
            getActiveInvocations()
                .then(response => {
                    this.invocationItems = response.data;
                    this.loading = false;
                    this.busy = false;
                })
                .catch(this.handleError);
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
