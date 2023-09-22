<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-3">
            <b-link :href="repo.repository_url" target="_blank">Show additional details and dependencies.</b-link>
        </div>
        <div>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                <span class="loading-message">Loading repository details...</span>
            </span>
            <div v-else>
                <b-alert v-if="error" variant="danger" show>
                    {{ error }}
                </b-alert>
                <div v-else class="border rounded">
                    <b-table borderless :items="repoTable" :fields="repoFields" class="text-center m-0">
                        <template v-slot:cell(numeric_revision)="data">
                            <span class="font-weight-bold">{{ data.value }}</span>
                        </template>
                        <template v-slot:cell(tools)="data">
                            <RepositoryTools :tools="data.value" />
                        </template>
                        <template v-slot:cell(profile)="data">
                            {{ data.value ? `+${data.value}` : "-" }}
                        </template>
                        <template v-slot:cell(missing_test_components)="data">
                            <span v-if="!data.value" :class="repoChecked" />
                            <span v-else :class="repoUnchecked" />
                        </template>
                        <template v-slot:cell(status)="row">
                            <span v-if="row.item.status">
                                <span
                                    v-if="!['Error', 'Installed', 'Uninstalled'].includes(row.item.status)"
                                    class="fa fa-spinner fa-spin" />
                                {{ row.item.status }}
                            </span>
                            <span v-else> - </span>
                        </template>
                        <template v-slot:cell(actions)="row">
                            <InstallationActions
                                :status="row.item.status"
                                @onInstall="setupRepository(row.item)"
                                @onUninstall="uninstallRepository(row.item)" />
                        </template>
                    </b-table>
                    <ConfigProvider v-slot="{ config }">
                        <ToolPanelViewProvider v-slot="{ currentPanel }" :panel-view="`default`" :set-default="false">
                            <InstallationSettings
                                v-if="showSettings"
                                :repo="repo"
                                :toolshed-url="toolshedUrl"
                                :changeset-revision="selectedChangeset"
                                :requires-panel="selectedRequiresPanel"
                                :current-panel="currentPanel"
                                :tool-dynamic-configs="config.tool_dynamic_configs"
                                @hide="onHide"
                                @ok="onOk" />
                        </ToolPanelViewProvider>
                    </ConfigProvider>
                </div>
            </div>
        </div>
    </b-card>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "../services";
import ConfigProvider from "components/providers/ConfigProvider";
import ToolPanelViewProvider from "components/providers/ToolPanelViewProvider";
import InstallationSettings from "./InstallationSettings.vue";
import InstallationActions from "./InstallationActions.vue";
import RepositoryTools from "./RepositoryTools.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        ConfigProvider,
        ToolPanelViewProvider,
        InstallationSettings,
        InstallationActions,
        RepositoryTools,
    },
    props: {
        repo: {
            type: Object,
            required: true,
        },
        toolshedUrl: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            repoChecked: "fa fa-check text-success",
            repoUnchecked: "fa fa-times text-danger",
            selectedChangeset: null,
            selectedRequiresPanel: false,
            repoTable: [],
            repoFields: [
                { key: "numeric_revision", label: "Revision" },
                { key: "tools", label: "Tools and Versions" },
                { key: "profile", label: "Requires" },
                { key: "missing_test_components", label: "Tests" },
                { key: "status" },
                { key: "actions", label: "", class: "toolshed-repo-actions" },
            ],
            showSettings: false,
            error: null,
            loading: true,
            delay: 2000,
        };
    },
    created() {
        this.services = new Services();
        this.load();
    },
    destroyed() {
        this.clearTimeout();
    },
    methods: {
        clearTimeout() {
            if (this.timeout) {
                clearTimeout(this.timeout);
            }
        },
        setTimeout() {
            this.clearTimeout();
            this.timeout = setTimeout(() => {
                this.loadInstalledRepositories();
            }, this.delay);
        },
        load() {
            this.services
                .getRepository(this.toolshedUrl, this.repo.id)
                .then((response) => {
                    this.repoTable = response;
                    this.loadInstalledRepositories();
                })
                .catch((error) => {
                    this.error = error;
                    this.loading = false;
                });
        },
        loadInstalledRepositories() {
            this.services
                .getInstalledRepositoriesByName(this.repo.name, this.repo.owner)
                .then((revisions) => {
                    let changed = false;
                    this.repoTable.forEach((x) => {
                        const revision = revisions[x.changeset_revision];
                        if (revision && revision.status !== x.status) {
                            x.status = revision.status;
                            x.installed = revision.installed;
                            changed = true;
                            return false;
                        }
                    });
                    if (changed) {
                        this.repoTable = [...this.repoTable];
                    }
                    this.setTimeout();
                    this.loading = false;
                })
                .catch((error) => {
                    this.error = error;
                    this.loading = false;
                });
        },
        onOk: function (details) {
            this.services
                .installRepository(details)
                .then((response) => {
                    this.showSettings = false;
                })
                .catch((error) => {
                    console.log(error);
                });
        },
        onHide: function () {
            this.showSettings = false;
        },
        setupRepository: function (details) {
            this.selectedChangeset = details.changeset_revision;
            this.selectedRequiresPanel =
                details.includes_tools_for_display_in_tool_panel ||
                details.repository.type == "repository_suite_definition";
            this.showSettings = true;
        },
        uninstallRepository: function (details) {
            this.services
                .uninstallRepository({
                    tool_shed_url: this.toolshedUrl,
                    name: this.repo.name,
                    owner: this.repo.owner,
                    changeset_revision: details.changeset_revision,
                })
                .catch((error) => {
                    this.error = error;
                });
        },
    },
};
</script>

<style lang="scss">
// make actions take up less space
.toolshed-repo-actions {
    width: 10%;
    min-width: 120px;
}
</style>
