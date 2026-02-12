<template>
    <DependencyIndexWrapper
        :error="error"
        :loading="loading"
        loading-message="Loading container resolution information">
        <template v-slot:header>
            <BRow class="m-1">
                <BForm inline>
                    <b>Resolution:</b>
                    <label class="mr-sm-2" for="manage-container-type">Resolve containers of type</label>
                    <BFormSelect
                        id="manage-container-type"
                        v-model="containerType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="containerTypeOptions" />

                    <label class="mr-sm-2" for="manage-resolver-type">using resolvers of type</label>
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

                    <label v-if="filterResolution != 'unresolved'" class="mr-sm-2" for="manage-filter-container-type">
                        Containers of type
                    </label>
                    <BFormSelect
                        v-if="filterResolution != 'unresolved'"
                        id="manage-filter-container-type"
                        v-model="filterContainerType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="containerTypeOptions" />

                    <label v-if="filterResolution != 'unresolved'" class="mr-sm-2" for="manage-filter-resolver-type">
                        Resolvers of type
                    </label>
                    <BFormSelect
                        v-if="filterResolution != 'unresolved'"
                        id="manage-filter-resolver-type"
                        v-model="filterResolverType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="resolverTypeOptions" />
                </BForm>
            </BRow>
        </template>

        <template v-slot:actions>
            <BRow class="m-1">
                <GButton class="mb-2 mr-sm-2 mb-sm-0" @click="installSelected">
                    <FontAwesomeIcon :icon="faPlus" />
                    Attempt Build
                </GButton>
            </BRow>
        </template>

        <template v-slot:body>
            <GTable id="containers-table" striped :fields="fields" :items="items" @row-clicked="showRowDetails">
                <template v-slot:cell(selected)="data">
                    <BFormCheckbox v-model="data.item.selected" />
                </template>

                <template v-slot:cell(requirement)="row">
                    <Requirements :requirements="row.item.requirements" />
                </template>

                <template v-slot:cell(resolution)="row">
                    <StatusDisplay :status="row.item.status" />
                </template>

                <template v-slot:cell(container)="row">
                    <ContainerDescription :container-description="row.item.status.container_description" />
                </template>

                <template v-slot:cell(resolver)="row">
                    <ContainerResolver :container-resolver="row.item.status.container_resolver" />
                </template>

                <template v-slot:cell(tool)="row">
                    <ToolDisplay :tool-id="row.item.tool_id" />
                </template>

                <template v-slot:row-details="row">
                    <ContainerResolutionDetails :resolution="row.item" />
                </template>
            </GTable>
        </template>
    </DependencyIndexWrapper>
</template>

<script>
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BForm, BFormCheckbox, BFormSelect, BRow } from "bootstrap-vue";
import _ from "underscore";

import { getContainerResolutionToolbox, resolveContainersWithInstall } from "../AdminServices";
import DependencyIndexMixin from "./DependencyIndexMixin";

import ContainerDescription from "@/components/admin/Dependencies/ContainerDescription.vue";
import ContainerResolutionDetails from "@/components/admin/Dependencies/ContainerResolutionDetails.vue";
import ContainerResolver, { DESCRIPTION } from "@/components/admin/Dependencies/ContainerResolver.vue";
import DependencyIndexWrapper from "@/components/admin/Dependencies/DependencyIndexWrapper.vue";
import Requirements from "@/components/admin/Dependencies/Requirements.vue";
import StatusDisplay from "@/components/admin/Dependencies/StatusDisplay.vue";
import ToolDisplay from "@/components/admin/Dependencies/ToolDisplay.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";

const RESOLVER_TYPE_OPTIONS = _.keys(DESCRIPTION).map((resolverType) => ({ value: resolverType, text: resolverType }));
RESOLVER_TYPE_OPTIONS.splice(0, 0, { value: null, text: "*any*" });

export default {
    components: {
        BForm,
        BFormCheckbox,
        BFormSelect,
        BRow,
        ContainerDescription,
        ContainerResolutionDetails,
        ContainerResolver,
        DependencyIndexWrapper,
        FontAwesomeIcon,
        GButton,
        GTable,
        Requirements,
        StatusDisplay,
        ToolDisplay,
    },
    mixins: [DependencyIndexMixin],
    data() {
        return {
            faPlus,
            error: null,
            loading: true,
            fields: [
                { key: "selected", label: "" },
                { key: "tool", label: "Tool" },
                { key: "requirement", label: "Requirements" },
                { key: "resolution", label: "Resolution" },
                { key: "resolver", label: "Resolver" },
                { key: "container", label: "Container" },
            ],
            containerType: null,
            containerTypeOptions: [
                { value: null, text: "*any*" },
                { value: "docker", text: "Docker" },
                { value: "singularity", text: "Singularity" },
            ],
            resolverType: null,
            resolverTypeOptions: RESOLVER_TYPE_OPTIONS,
            filterResolution: null,
            filterResolverType: null,
            filterContainerType: null,
            resolutions: [],
        };
    },
    computed: {
        items: function () {
            return this.resolutions
                .filter((resolution) => {
                    if (this.filterResolution == "unresolved" && resolution.status.dependency_type != null) {
                        return false;
                    }
                    if (this.filterResolution == "resolved" && resolution.status.dependency_type == null) {
                        return false;
                    }
                    if (this.filterContainerType) {
                        if (
                            !resolution.status.container_description ||
                            resolution.status.container_description.type != this.filterContainerType
                        ) {
                            return false;
                        }
                    }
                    if (this.filterResolverType) {
                        if (
                            !resolution.status.container_description ||
                            resolution.status.container_resolver.resolver_type != this.filterResolverType
                        ) {
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
                        tool_id: resolution.tool_id,
                        _showDetails: false,
                    };
                });
        },
    },
    watch: {
        containerType: function (val) {
            this.load();
        },
        resolverType: function (val) {
            this.load();
        },
        filterResolution: function (val) {
            if (val == "unresolved") {
                this.filterResolverType = null;
                this.filterContainerType = null;
            }
        },
    },
    methods: {
        load() {
            this.loading = true;
            const params = this.apiParams();
            getContainerResolutionToolbox(params)
                .then((resolutions) => {
                    this.resolutions = resolutions;
                    this.loading = false;
                })
                .catch(this.handleError);
        },
        installSelected() {
            this.loading = true;
            resolveContainersWithInstall(this.selectedToolIds(), this.apiParams())
                .then((resolutions) => {
                    this.resolutions = resolutions;
                    this.loading = false;
                })
                .catch(this.handleError);
        },
        apiParams() {
            const params = {};
            if (this.containerType) {
                params.container_type = this.containerType;
            }
            if (this.resolverType) {
                params.resolver_type = this.resolverType;
            }
            return params;
        },
        selectedToolIds() {
            return this.items.filter((item) => item.selected).map((item) => item.tool_id);
        },
    },
};
</script>
