<template>
    <div v-if="showStatus">
        <span v-if="loading">
            <span class="fa fa-spinner fa-spin" /> Loading repository details...
        </span>
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
        </div>
    </div>
    <installationsettings v-else :toolshedUrl="toolshedUrl" :repoChangeset="repoChangeset" />
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
                installed: {
                    label: ""
                }
            },
            showStatus: true,
            loading: true
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
                });
        },
        loadInstalledRepositories() {
            this.services
                .getInstalledRepositories(this.repo)
                .then((revisions) => {
                    this.repoTable.forEach(x => {
                        x.installed = revisions[x.changeset_revision];
                    });
                    this.loading = false;
                })
                .catch(error => {
                    alert(error);
                });
        },
        setupRepository: function(details) {
            this.showStatus = false;
            this.repoChangeset = details.changeset_revision;
        },
        uninstallRepository: function(details) {
            this.services.uninstallRepository({
                tool_shed_url: this.toolshedUrl,
                name: this.repo.name,
                owner: this.repo.repo_owner_username,
                changeset_revision: details.changeset_revision
            }).then(response => {
                this.repoTable.forEach(x => {
                    if (x.changeset_revision == details.changeset_revision) {
                        x.installed = false;
                    }
                });
                this.repoTable = [...this.repoTable];
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
