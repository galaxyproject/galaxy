<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" :message="loadingMessage" />
            <!-- search header borrowed from WorkflowList.vue -->
            <b-row class="mb-3">
                <b-col cols="6">
                    <b-input
                        id="tool-search"
                        class="m-1"
                        name="query"
                        placeholder="Search Tool IDs"
                        autocomplete="off"
                        type="text"
                        v-model="filter"
                    />
                </b-col>
            </b-row>
            <b-table id="manage-tools-table" striped :fields="fields" :items="items" @row-clicked="showRowDetails" :filter="filter">
                <template v-slot:cell(link)="data">
                    <b-button
                        v-b-tooltip.hover.bottom
                        title="Run Tools"
                        class="btn-sm fa fa-link"
                        :href="toolLink(data)"
                    />
                </template>
                <template slot="row-details" slot-scope="row">
                    <tool-details :toolId="row.item.tool.id" :toolVersion="row.item.tool.version" :repo="row.item.repo" />
                </template>
            </b-table>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { getTools } from "./AdminServices.js";
import ToolDetails from "./ToolDetails.vue";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
        ToolDetails
    },
    data() {
        return {
            loading: true,
            loadingMessage: 'Loading available Galaxy tools...',
            error: null,
            fields: [{ key: "tool_id", label: "ID", sortable: true }, { key: "tool_version", label: "Version", sortable: true }, { key: "link", label: "" }],
            tools: [],
            filter: ""
        };
    },
    created() {
        this.load();
    },
    computed: {
        items: function() {
            return this.tools.map(tool => {
                let repo = null;
                if ( tool.tool_shed_repository ) {
                    repo = {};
                    // TODO: relax tool_shed_url on the server side - shouldn't need to know http vs. https and
                    // shouldn't depend on last /.
                    repo.tool_shed_url = "https://" + tool.tool_shed_repository.tool_shed + "/";
                    repo.owner = tool.tool_shed_repository.owner;
                    repo.name = tool.tool_shed_repository.name;
                }
                return { tool: tool, tool_id: tool.id, tool_version: tool.version, repo: repo, selected: false, _showDetails: false };
            });
        },
    },
    methods: {
        load() {
            this.loading = true;
            this.filter = "";
            getTools()
                .then(tools => {
                    this.tools = tools;
                    this.loading = false;
                })
                .catch(this.handleError);
        },
        showRowDetails(row, index, e) {
            if (e.target.nodeName != "A") {
                row._showDetails = !row._showDetails;
            }
        },
        toolLink(row) {
            // why doesn't ${getAppRoot()}${link} work?
            return `${row.item.tool.link}`;
        },
        handleError(e) {
            this.error = e;
        }
    }
};
</script>
