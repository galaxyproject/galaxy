<template>
    <div>
        <span v-if="loading">
            <span class="fa fa-spinner fa-spin" /> Loading repository details...
        </span>
        <div v-else>
            <b-alert v-if="error" variant="danger" show>
                {{ error }}
            </b-alert>
            <div v-else class="border rounded">
                <b-table
                    borderless
                    :items="repoTable"
                    :fields="repoFields"
                    class="text_align_center m-0"
                >
                    <template slot="numeric_revision" slot-scope="data">
                        <span class="font-weight-bold">{{data.value}}</span>
                    </template>
                    <template slot="includes_tools" slot-scope="data">
                        <span v-if="data.value" :class="repoChecked"/>
                        <span v-else :class="repoUnchecked"/>
                    </template>
                    <template slot="includes_workflows" slot-scope="data">
                        <span v-if="data.value" :class="repoChecked"/>
                        <span v-else :class="repoUnchecked"/>
                    </template>
                    <template slot="includes_datatypes" slot-scope="data">
                        <span v-if="data.value" :class="repoChecked"/>
                        <span v-else :class="repoUnchecked"/>
                    </template>
                    <template slot="includes_tool_dependencies" slot-scope="data">
                        <span v-if="data.value" :class="repoChecked"/>
                        <span v-else :class="repoUnchecked"/>
                    </template>
                    <template slot="includes_tools_for_display_in_tool_panel" slot-scope="data">
                        <span v-if="data.value" :class="repoChecked"/>
                        <span v-else :class="repoUnchecked"/>
                    </template>
                    <template slot="status" slot-scope="data">
                        <b-button v-if="data.value == 'Installed'" :class="statusOk" disabled>
                            {{ data.value }}
                        </b-button>
                        <b-button v-else :class="statusInfo" disabled>
                            {{ data.value }}
                        </b-button>
                    </template>
                    <template slot="installed" slot-scope="row">
                        <b-button v-if="!row.item.installed"
                            class="btn-sm"
                            variant="primary"
                            @click="setupRepository(row.item)">
                                Install
                        </b-button>
                        <b-button v-else
                            class="btn-sm"
                            variant="danger"
                            @click="uninstallRepository(row.item)">
                                Uninstall
                        </b-button>
                    </template>
                </b-table>
                <installationsettings
                    v-if="showSettings"
                    :repo="repo"
                    :toolshedUrl="toolshedUrl"
                    :repoChangeset="repoChangeset"
                    :repoNumeric="repoNumeric"
                    @hide="onHide"
                    @ok="onOk"
                />
            </div>
        </div>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
import InstallationSettings from "./InstallationSettings.vue";
export default {
    components: {
        installationsettings: InstallationSettings
    },
    props: ["repo", "toolshedUrl"],
    data() {
        const galaxy = getGalaxyInstance();
        return {
            statusOk: "btn-sm btn-success font-weight-bold rounded-0",
            statusInfo: "btn-sm btn-info rounded-0",
            repoChecked: "fa fa-check text-success",
            repoUnchecked: "fa fa-times text-danger",
            repoChangeset: null,
            repoTable: [],
            repoFields: {
                numeric_revision: {
                    label: "Revision"
                },
                includes_tools: {
                    label: "Tools"
                },
                includes_workflows: {
                    label: "Workflows"
                },
                includes_datatypes: {
                    label: "Datatypes"
                },
                includes_tool_dependencies: {
                    label: "Dependencies"
                },
                status: {
                    label: "Status"
                },
                installed: {
                    label: ""
                }
            },
            showSettings: false,
            error: null,
            loading: true,
            timeout: 1000
        };
    },
    created() {
        this.services = new Services();
        this.loadDetails();
    },
    methods: {
        loadDetails() {
            this.services
                .getDetails(this.toolshedUrl, this.repo.id)
                .then(response => {
                    this.repoTable = response;
                    this.loadInstalledRepositories();
                }).catch(error => {
                    this.error = error;
                    this.loading = false;
                });
        },
        listenInstalledRepositories() {
            this.listener = setTimeout(() => {
                this.loadInstalledRepositories();
            }, this.timeout);
        },
        loadInstalledRepositories() {
            this.services
                .getInstalledRepositories(this.repo)
                .then((revisions) => {
                    let changed = false;
                    this.repoTable.forEach(x => {
                        const revision = revisions[x.changeset_revision];
                        if (revision) {
                            if (revision.installed !== x.installed) {
                                x.installed = revision.installed;
                                changed = true;
                            }
                            if (revision.status !== x.status) {
                                x.status = revision.status;
                                changed = true;
                            }
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
            alert('stateok');
        },
        onHide: function() {
            this.showSettings = false;
        },
        setupRepository: function(details) {
            this.repoChangeset = details.changeset_revision;
            this.repoNumeric = details.numeric_revision;
            this.showSettings = true;
        },
        uninstallRepository: function(details) {
            this.services.uninstallRepository({
                tool_shed_url: this.toolshedUrl,
                name: this.repo.name,
                owner: this.repo.repo_owner_username,
                changeset_revision: details.changeset_revision
            }).catch(error => {
                alert(error);
            });
        }
    }
};
</script>
<style>
.text_align_center {
    text-align: center;
}
</style>
