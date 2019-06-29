<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-3">
            <b-link :href="repo.repository_url" target="_blank">Show additional details and dependencies.</b-link>
        </div>
        <div>
            <span v-if="loading">
                <span class="fa fa-spinner fa-spin" />
                Loading repository details...
            </span>
            <div v-else>
                <b-alert v-if="error" variant="danger" show>
                    {{ error }}
                </b-alert>
                <div v-else class="border rounded">
                    <b-table borderless :items="repoTable" :fields="repoFields" class="text-center m-0">
                        <template slot="numeric_revision" slot-scope="data">
                            <span class="font-weight-bold">{{ data.value }}</span>
                        </template>
                        <template slot="tools" slot-scope="data">
                            <repositorytools :tools="data.value" />
                        </template>
                        <template slot="profile" slot-scope="data">
                            {{ data.value ? `+${data.value}` : "-" }}
                        </template>
                        <template slot="missing_test_components" slot-scope="data">
                            <span v-if="!data.value" :class="repoChecked" />
                            <span v-else :class="repoUnchecked" />
                        </template>
                        <template slot="actions" slot-scope="row">
                            <installationbutton
                                :installed="row.item.installed"
                                :status="row.item.status"
                                @onInstall="setupRepository(row.item)"
                                @onUninstall="uninstallRepository(row.item)"
                            />
                        </template>
                    </b-table>
                    <installationsettings
                        v-if="showSettings"
                        :repo="repo"
                        :toolshedUrl="toolshedUrl"
                        :changesetRevision="selectedChangeset"
                        :requiresPanel="selectedRequiresPanel"
                        @hide="onHide"
                        @ok="onOk"
                    />
                </div>
            </div>
        </div>
    </b-card>
</template>
<script>
import { Services } from "./services.js";
import InstallationSettings from "./InstallationSettings.vue";
import InstallationButton from "./InstallationButton.vue";
import RepositoryTools from "./RepositoryTools.vue";
export default {
    components: {
        installationsettings: InstallationSettings,
        installationbutton: InstallationButton,
        repositorytools: RepositoryTools
    },
    props: ["repo", "toolshedUrl"],
    data() {
        return {
            repoChecked: "fa fa-check text-success",
            repoUnchecked: "fa fa-times text-danger",
            selectedChangeset: null,
            selectedRequiresPanel: false,
            repoTable: [],
            repoFields: {
                numeric_revision: {
                    label: "Revision"
                },
                tools: {
                    label: "Tools and Versions"
                },
                profile: {
                    label: "Requires"
                },
                missing_test_components: {
                    label: "Tests"
                },
                actions: {
                    label: ""
                }
            },
            showSettings: false,
            error: null,
            loading: true,
            delay: 2000
        };
    },
    created() {
        this.services = new Services();
        this.loadDetails();
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
        loadDetails() {
            this.services
                .getDetails(this.toolshedUrl, this.repo.id)
                .then(response => {
                    this.repoTable = response;
                    this.loadInstalledRepositories();
                })
                .catch(error => {
                    this.error = error;
                    this.loading = false;
                });
        },
        listenInstalledRepositories() {
            this.clearTimeout();
            this.timeout = setTimeout(() => {
                this.loadInstalledRepositories();
            }, this.delay);
        },
        loadInstalledRepositories() {
            this.services
                .getInstalledRepositories(this.repo)
                .then(revisions => {
                    let changed = false;
                    this.repoTable.forEach(x => {
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
                    this.listenInstalledRepositories();
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                    this.loading = false;
                });
        },
        onOk: function() {
            this.showSettings = false;
        },
        onHide: function() {
            this.showSettings = false;
        },
        setupRepository: function(details) {
            this.selectedChangeset = details.changeset_revision;
            this.selectedRequiresPanel = details.includes_tools_for_display_in_tool_panel || details.repository.type == "repository_suite_definition";
            this.showSettings = true;
        },
        uninstallRepository: function(details) {
            this.services
                .uninstallRepository({
                    tool_shed_url: this.toolshedUrl,
                    name: this.repo.name,
                    owner: this.repo.repo_owner_username,
                    changeset_revision: details.changeset_revision
                })
                .catch(error => {
                    this.error = error;
                });
        }
    }
};
</script>
