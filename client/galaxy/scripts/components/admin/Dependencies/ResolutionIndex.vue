<template>
    <dependency-index-wrapper
        :error="error"
        :loading="loading"
        loading-message="Loading tool requirement resolution information"
    >
        <template v-slot:header>
            <div>
                <b-form inline>
                    <b>Resolution:</b>
                    <label class="mr-sm-2" for="manage-resolver-type">Using resolvers of type</label>
                    <b-form-select
                        class="mb-2 mr-sm-2 mb-sm-0"
                        id="manage-resolver-type"
                        v-model="resolverType"
                        :options="resolverTypeOptions"
                    ></b-form-select>
                </b-form>
            </div>
            <div>
                <b-form inline>
                    <b>Filter:</b>
                    <label class="mr-sm-2" for="manage-filter-resolution">Resolution</label>
                    <b-form-select
                        class="mb-2 mr-sm-2 mb-sm-0"
                        id="manage-filter-resolution"
                        v-model="filterResolution"
                    >
                        <option :value="null">*any*</option>
                        <option value="unresolved">Unresolved</option>
                        <option value="resolved">Resolved</option>
                    </b-form-select>
                </b-form>
            </div>
        </template>
        <template v-slot:body>
            <b-table id="requirements-table" striped :fields="fields" :items="items" @row-clicked="showRowDetails">
                <template v-slot:cell(selected)="data">
                    <b-form-checkbox v-model="data.item.selected"></b-form-checkbox>
                </template>
                <template v-slot:cell(requirement)="row">
                    <requirements :requirements="row.item.requirements" />
                </template>
                <template v-slot:cell(resolution)="row">
                    <statuses :statuses="row.item.status" />
                </template>
                <template v-slot:cell(tools)="row">
                    <tools :tool-ids="row.item.tool_ids" />
                </template>
                <template v-slot:cell(tool)="row">
                    <tool-display :tool-id="row.item.tool" />
                </template>
                <template slot="row-details" slot-scope="row">
                    <resolution-details :resolution="row.item" />
                </template>
            </b-table>
        </template>
        <template v-slot:actions>
            <div>
                <b-button @click="installSelected">
                    <!-- v-bind:disabled="!hasSelection"  -->
                    Install
                </b-button>
                <b-button @click="uninstallSelected">
                    <!-- v-bind:disabled="!hasSelection"  -->
                    Uninstall
                </b-button>
                <b-button @click="setExpandToolIds(true)" v-if="!expandToolIds">
                    Expand Tools
                </b-button>
                <b-button @click="setExpandToolIds(false)" v-if="expandToolIds">
                    Group by Requirements
                </b-button>
            </div>
        </template>
    </dependency-index-wrapper>
</template>
<script>
import _ from "underscore";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import DependencyIndexMixin from "./DependencyIndexMixin";
import ResolutionDetails from "./ResolutionDetails";
import { getToolboxDependencies, installDependencies, uninstallDependencies } from "../AdminServices.js";

Vue.use(BootstrapVue);

export const RESOLVER_DESCRIPTIONS = {
    conda: "",
    tool_shed_packages: "",
    galaxy_packages: "",
    lmod: "",
    module: ""
};
const RESOLVER_TYPE_OPTIONS = _.keys(RESOLVER_DESCRIPTIONS).map(resolverType => ({
    value: resolverType,
    text: resolverType
}));
RESOLVER_TYPE_OPTIONS.splice(0, 0, { value: null, text: "*any*" });

export default {
    mixins: [DependencyIndexMixin],
    components: { ResolutionDetails },
    data() {
        return {
            expandToolIds: false,
            error: null,
            loading: true,
            resolverType: null,
            resolverTypeOptions: RESOLVER_TYPE_OPTIONS,
            baseFields: [{ key: "selected", label: "" }, { key: "requirement" }, { key: "resolution" }],
            filterResolution: null,
            requirements: []
        };
    },
    watch: {
        resolverType: function(val) {
            this.load();
        }
    },
    computed: {
        fields: function() {
            const fields = this.baseFields.slice();
            if (this.expandToolIds) {
                fields.splice(1, 0, { key: "tool", label: "Tool" });
            } else {
                fields.splice(3, 0, { key: "tools", label: "Tools" });
            }
            return fields;
        },
        items: function() {
            let items = this.requirements
                .filter(resolution => {
                    if (this.filterResolution) {
                        let anyUnresolved = resolution.status.length == 0; // odd logic here, but we call no requirements unresolved in the GUI :(
                        for (const status of resolution.status) {
                            console.log(status);
                            anyUnresolved = anyUnresolved || status.dependency_type == null;
                        }
                        if (this.filterResolution == "resolved" && anyUnresolved) {
                            return false;
                        }
                        if (this.filterResolution == "unresolved" && !anyUnresolved) {
                            return false;
                        }
                    }
                    return true;
                })
                .map(resolution => {
                    return {
                        selected: false,
                        requirements: resolution.requirements,
                        status: resolution.status,
                        tool_ids: resolution.tool_ids,
                        _showDetails: false
                    };
                });
            if (this.expandToolIds) {
                const toolItems = [];
                for (const requirementItem of items) {
                    for (const toolId of requirementItem["tool_ids"]) {
                        toolItems.push({ ...requirementItem, tool: toolId });
                    }
                }
                items = toolItems;
            }
            return items;
        },
        selectedToolIds: function() {
            const toolIds = [];
            for (const item of this.items) {
                if (item["selected"]) {
                    const selectedReqIds = item["tool_ids"];
                    if (selectedReqIds) {
                        toolIds.push(selectedReqIds[0]);
                    }
                }
            }
            return toolIds;
        }
    },
    methods: {
        load() {
            this.loading = true;
            getToolboxDependencies(this.apiParams())
                .then(requirements => {
                    this.requirements = requirements;
                    this.loading = false;
                })
                .catch(this.handleError);
        },
        apiParams() {
            const params = {};
            if (this.expandToolIds) {
                params.index_by = "tools";
            }
            if (this.resolverType) {
                params.resolver_type = this.resolverType;
            }
            return params;
        },
        installSelected() {
            this.loading = true;
            installDependencies(this.selectedToolIds)
                .then(() => {
                    this.load();
                })
                .catch(this.handleError);
        },
        uninstallSelected() {
            this.loading = true;
            uninstallDependencies(this.selectedToolIds)
                .then(() => {
                    this.load();
                })
                .catch(this.handleError);
        },
        setExpandToolIds(expandToolIds) {
            this.expandToolIds = expandToolIds;
            this.load();
        }
    }
};
</script>
