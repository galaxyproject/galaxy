<template>
    <dependency-index-wrapper
        :error="error"
        :loading="loading"
        loading-message="Loading container resolution information">
        <template v-slot:header>
            <b-row class="m-1">
                <b-form inline>
                    <b>Resolution:</b>
                    <label class="mr-sm-2" for="manage-container-type">Resolve containers of type</label>
                    <b-form-select
                        id="manage-container-type"
                        v-model="containerType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="containerTypeOptions"></b-form-select>
                    <label class="mr-sm-2" for="manage-resolver-type">using resolvers of type</label>
                    <b-form-select
                        id="manage-resolver-type"
                        v-model="resolverType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="resolverTypeOptions"></b-form-select>
                </b-form>
            </b-row>
            <b-row class="m-1">
                <b-form inline>
                    <b>Filter:</b>
                    <label class="mr-sm-2" for="manage-filter-resolution">Resolution</label>
                    <b-form-select
                        id="manage-filter-resolution"
                        v-model="filterResolution"
                        class="mb-2 mr-sm-2 mb-sm-0">
                        <option :value="null">*any*</option>
                        <option value="unresolved">Unresolved</option>
                        <option value="resolved">Resolved</option>
                    </b-form-select>
                    <label v-if="filterResolution != 'unresolved'" class="mr-sm-2" for="manage-filter-container-type"
                        >Containers of type</label
                    >
                    <b-form-select
                        v-if="filterResolution != 'unresolved'"
                        id="manage-filter-container-type"
                        v-model="filterContainerType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="containerTypeOptions"></b-form-select>
                    <label v-if="filterResolution != 'unresolved'" class="mr-sm-2" for="manage-filter-resolver-type"
                        >Resolvers of type</label
                    >
                    <b-form-select
                        v-if="filterResolution != 'unresolved'"
                        id="manage-filter-resolver-type"
                        v-model="filterResolverType"
                        class="mb-2 mr-sm-2 mb-sm-0"
                        :options="resolverTypeOptions"></b-form-select>
                </b-form>
            </b-row>
        </template>
        <template v-slot:actions>
            <b-row class="m-1">
                <GButton class="mb-2 mr-sm-2 mb-sm-0" @click="installSelected">
                    <!-- v-bind:disabled="!hasSelection"  -->
                    <span class="fa fa-plus" />
                    Attempt Build
                </GButton>
            </b-row>
        </template>
        <template v-slot:body>
            <b-table id="containers-table" striped :fields="fields" :items="items" @row-clicked="showRowDetails">
                <template v-slot:cell(selected)="data">
                    <b-form-checkbox v-model="data.item.selected"></b-form-checkbox>
                </template>
                <template v-slot:cell(requirement)="row">
                    <requirements :requirements="row.item.requirements" />
                </template>
                <template v-slot:cell(resolution)="row">
                    <status-display :status="row.item.status" />
                </template>
                <template v-slot:cell(container)="row">
                    <container-description :container-description="row.item.status.container_description" />
                </template>
                <template v-slot:cell(resolver)="row">
                    <container-resolver :container-resolver="row.item.status.container_resolver" />
                </template>
                <template v-slot:cell(tool)="row">
                    <tool-display :tool-id="row.item.tool_id" />
                </template>
                <template v-slot:row-details="row">
                    <ContainerResolutionDetails :resolution="row.item" />
                </template>
            </b-table>
        </template>
    </dependency-index-wrapper>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import _ from "underscore";
import Vue from "vue";

import { getContainerResolutionToolbox, resolveContainersWithInstall } from "../AdminServices";
import ContainerResolutionDetails from "./ContainerResolutionDetails";
import { DESCRIPTION } from "./ContainerResolver";
import DependencyIndexMixin from "./DependencyIndexMixin";

import GButton from "@/components/BaseComponents/GButton.vue";

Vue.use(BootstrapVue);

const RESOLVER_TYPE_OPTIONS = _.keys(DESCRIPTION).map((resolverType) => ({ value: resolverType, text: resolverType }));
RESOLVER_TYPE_OPTIONS.splice(0, 0, { value: null, text: "*any*" });

export default {
    components: { ContainerResolutionDetails, GButton },
    mixins: [DependencyIndexMixin],
    data() {
        return {
            error: null,
            loading: true,
            fields: [
                { key: "selected", label: "" },
                { key: "tool" },
                { key: "requirement", label: "Requirements" },
                { key: "resolution" },
                { key: "resolver" },
                { key: "container" },
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
