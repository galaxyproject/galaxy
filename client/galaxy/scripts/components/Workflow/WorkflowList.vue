<template>
    <div class="ui-thumbnails">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <div class="search-input">
                <input
                    class="search-query parent-width"
                    name="query"
                    placeholder="search workflows"
                    autocomplete="off"
                    type="text"
                    v-model="search"
                />
            </div>
            <b-table striped :fields="fields" :items="workflows">
                <template slot="name" slot-scope="row">
                    <workflowdropdown :workflow="row.item"/>
                </template>
                <template slot="execute" slot-scope="row">
                    <b-button
                      class="btn-sm btn-primary fa fa-play"
                      @click.stop="clickExecute(row.item)"
                    />
                </template>
            </b-table>
        </div>
    </div>
</template>
<script>
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
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
            search: "",
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
    created() {
        const Galaxy = getGalaxyInstance();
        let url = `${getAppRoot()}api/workflows`;
        axios
            .get(url)
            .then(response => {
                this.workflows = response.data;
                for (workflow of this.workflows) {
                    workflow.create_time = workflow.create_time.substring(0, 10);
                    if (workflow.annotations && workflow.annotations.length > 0) {
                        workflow.annotations = workflow.annotations[0].trim();
                    }
                    if (!workflow.annotations) {
                        workflow.annotations = "Not available.";
                    }
                }
            })
            .catch(e => {
                this.error = this._errorMessage(e);
            });
    },
    methods: {
        select: function(workflow) {
        },
        create: function(workflow) {
        },
        clickExecute: function(workflow) {
            window.location = `${getAppRoot()}workflows/run?id=${workflow.id}`;
        },
        match: function(workflow) {
            return (
                !this.search ||
                workflow.name.indexOf(this.search) != -1 ||
                (workflow.description && workflow.description.indexOf(this.search) != -1)
            );
        },
        _errorMessage: function(e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        }
    }
};
</script>
