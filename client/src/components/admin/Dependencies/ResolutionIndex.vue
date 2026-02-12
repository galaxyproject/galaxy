<template>
    <DependencyIndexWrapper
        :error="error"
        :loading="loading"
        loading-message="Loading tool requirement resolution information">
        <template v-slot:header>
            <BRow class="m-1">
                <BForm inline>
                    <b>Resolution:</b>
                    <label class="mr-sm-2" for="manage-resolver-type">Using resolvers of type</label>
                    <BFormSelect
                        id="manage-resolver-type"
                        v-model="resolverType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="resolverTypeOptions" />
                </BForm>
            </BRow>

            <BRow class="m-1">
                <BForm inline>
                    <b>Filter:</b>
                    <label class="mr-sm-2" for="manage-filter-resolution">Resolution</label>
                    <BFormSelect id="manage-filter-resolution" v-model="filterResolution" class="mb-2 mr-sm-2 mb-sm-0">
                        <option :value="null">*any*</option>
                        <option value="unresolved">Unresolved</option>
                        <option value="resolved">Resolved</option>
                    </BFormSelect>
                </BForm>
            </BRow>
        </template>

        <template v-slot:body>
            <GTable id="requirements-table" striped :fields="fields" :items="items" @row-clicked="showRowDetails">
                <template v-slot:cell(selected)="data">
                    <BFormCheckbox v-model="data.item.selected" @change="changeToggleCheckboxState($event)" />
                </template>

                <template v-slot:head(selected)="">
                    <BFormCheckbox v-model="toggleState" @change="toggleSelectAll" />
                </template>

                <template v-slot:cell(requirement)="row">
                    <Requirements :requirements="row.item.requirements" />
                </template>

                <template v-slot:cell(resolution)="row">
                    <Statuses :statuses="row.item.status" />
                </template>

                <template v-slot:cell(tools)="row">
                    <Tools :tool-ids="row.item.tool_ids" />
                </template>

                <template v-slot:cell(tool)="row">
                    <ToolDisplay :tool-id="row.item.tool" />
                </template>

                <template v-slot:row-details="row">
                    <ResolutionDetails :resolution="row.item" />
                </template>
            </GTable>
        </template>

        <template v-slot:actions>
            <BRow class="m-1">
                <GButton class="m-1" @click="installSelected">
                    <FontAwesomeIcon :icon="faPlus" />
                    Install
                </GButton>

                <GButton class="m-1" @click="uninstallSelected">
                    <FontAwesomeIcon :icon="faMinus" />
                    Uninstall
                </GButton>

                <GButton v-if="!expandToolIds" class="m-1" @click="setExpandToolIds(true)">
                    <FontAwesomeIcon :icon="faChevronDown" />
                    Expand Tools
                </GButton>

                <GButton v-if="expandToolIds" class="m-1" @click="setExpandToolIds(false)">
                    <FontAwesomeIcon :icon="faChevronUp" />
                    Group by Requirements
                </GButton>
            </BRow>
        </template>
    </DependencyIndexWrapper>
</template>

<script>
import { faChevronDown, faChevronUp, faMinus, faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BForm, BFormCheckbox, BFormSelect, BRow } from "bootstrap-vue";
import _ from "underscore";

import { getToolboxDependencies, installDependencies, uninstallDependencies } from "../AdminServices";
import DependencyIndexMixin from "./DependencyIndexMixin";

import ResolutionDetails from "./ResolutionDetails.vue";
import DependencyIndexWrapper from "@/components/admin/Dependencies/DependencyIndexWrapper.vue";
import Requirements from "@/components/admin/Dependencies/Requirements.vue";
import Statuses from "@/components/admin/Dependencies/Statuses.vue";
import ToolDisplay from "@/components/admin/Dependencies/ToolDisplay.vue";
import Tools from "@/components/admin/Dependencies/Tools.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";

export const RESOLVER_DESCRIPTIONS = {
    conda: "",
    tool_shed_packages: "",
    galaxy_packages: "",
    lmod: "",
    module: "",
};
const RESOLVER_TYPE_OPTIONS = _.keys(RESOLVER_DESCRIPTIONS).map((resolverType) => ({
    value: resolverType,
    text: resolverType,
}));
RESOLVER_TYPE_OPTIONS.splice(0, 0, { value: null, text: "*any*" });

export default {
    components: {
        BForm,
        BFormCheckbox,
        BFormSelect,
        BRow,
        FontAwesomeIcon,
        DependencyIndexWrapper,
        GButton,
        GTable,
        ResolutionDetails,
        Requirements,
        Statuses,
        ToolDisplay,
        Tools,
    },
    mixins: [DependencyIndexMixin],
    data() {
        return {
            faChevronDown,
            faChevronUp,
            faMinus,
            faPlus,
            toggleState: false,
            expandToolIds: false,
            error: null,
            loading: true,
            resolverType: null,
            resolverTypeOptions: RESOLVER_TYPE_OPTIONS,
            baseFields: [{ key: "selected", label: "" }, { key: "requirement" }, { key: "resolution" }],
            filterResolution: null,
            requirements: [],
        };
    },
    computed: {
        fields: function () {
            const fields = this.baseFields.slice();
            if (this.expandToolIds) {
                fields.splice(1, 0, { key: "tool", label: "Tool" });
            } else {
                fields.splice(3, 0, { key: "tools", label: "Tools" });
            }
            return fields;
        },
        items: function () {
            let items = this.requirements
                .filter((resolution) => {
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
                .map((resolution) => {
                    return {
                        selected: false,
                        requirements: resolution.requirements,
                        status: resolution.status,
                        tool_ids: resolution.tool_ids,
                        _showDetails: false,
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
        selectedToolIds: function () {
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
        },
    },
    watch: {
        resolverType: function (val) {
            this.load();
        },
    },
    methods: {
        unchecked: function () {
            return this.items.filter((item) => item.selected === false);
        },
        changeToggleCheckboxState(event) {
            if (event && this.unchecked().length === 1) {
                this.toggleState = true;
            } else {
                this.toggleState = false;
            }
        },
        toggleSelectAll: function (event) {
            this.items.forEach((item) => (item.selected = event));
        },
        load() {
            this.loading = true;
            getToolboxDependencies(this.apiParams())
                .then((requirements) => {
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
        },
    },
};
</script>
