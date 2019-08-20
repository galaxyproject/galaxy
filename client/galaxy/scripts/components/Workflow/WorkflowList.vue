<template>
    <div>
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                Loading workflows...
            </span>
            <div v-else>
                <b-row class="mb-3">
                    <b-col cols="8">
                        <b-input
                            class="m-1"
                            name="query"
                            placeholder="search workflows"
                            autocomplete="off"
                            type="text"
                            v-model="filter"
                        />
                    </b-col>
                    <b-col>
                        <span class="float-right">
                            <b-button class="m-1" @click="createWorkflow">
                                <span class="fa fa-plus"/>
                                Create
                            </b-button>
                            <b-button class="m-1" @click="importWorkflow">
                                <span class="fa fa-upload"/>
                                Import
                            </b-button>
                        </span>
                    </b-col>
                </b-row>
                <b-table striped :fields="fields" :items="workflows" :filter="filter" @filtered="filtered">
                    <template slot="name" slot-scope="row">
                        <workflowdropdown :workflow="row.item"/>
                    </template>
                    <template slot="execute" slot-scope="row">
                        <b-button
                          class="btn-sm btn-primary fa fa-play"
                          @click.stop="executeWorkflow(row.item)"
                        />
                    </template>
                </b-table>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ this.filter }}</span>.
                </div>
                <div v-if="showNotAvailable">
                    No workflows found. You may create or import new workflows.
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import WorkflowDropdown from "./WorkflowDropdown.vue";

export default {
    components: {
        workflowdropdown: WorkflowDropdown
    },
    data() {
        return {
            classChecked: "fa fa-check text-success",
            classUnchecked: "fa fa-times text-danger",
            workflows: [],
            loading: true,
            nWorkflows: 0,
            filter: "",
            error: null,
            fields: {
                name: {
                    sortable: true
                },
                annotations: {
                    label: "Description"
                },
                create_time: {
                    label: "Created"
                },
                execute: {
                    label: ""
                }
            }
        };
    },
    computed: {
        showNotFound() {
            return this.nWorkflows === 0 && this.filter;
        },
        showNotAvailable() {
            return this.nWorkflows === 0 && !this.filter;
        }
    },
    created() {
        let url = `${getAppRoot()}api/workflows`;
        this.loading = true;
        this.filter = "";
        axios
            .get(url)
            .then(response => {
                this.workflows = response.data;
                this.nWorkflows = this.workflows.length;
                for (workflow of this.workflows) {
                    workflow.create_time = workflow.create_time.substring(0, 10);
                    if (workflow.annotations && workflow.annotations.length > 0) {
                        workflow.annotations = workflow.annotations[0].trim();
                    }
                    if (!workflow.annotations) {
                        workflow.annotations = "Not available.";
                    }
                }
                this.loading = false;
            })
            .catch(e => {
                this.error = this._errorMessage(e);
            });
    },
    methods: {
        filtered: function(items) {
            this.nWorkflows = items.length;
        },
        createWorkflow: function(workflow) {
            window.location = `${getAppRoot()}workflows/create`;
        },
        importWorkflow: function(workflow) {
            window.location = `${getAppRoot()}workflows/import`;
        },
        executeWorkflow: function(workflow) {
            window.location = `${getAppRoot()}workflows/run?id=${workflow.id}`;
        },
        _errorMessage: function(e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        }
    }
};
</script>
