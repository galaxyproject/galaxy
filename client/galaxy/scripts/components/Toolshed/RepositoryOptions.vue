<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-1">
            <b-link :href="repo.repository_url" target="_blank">Show additional details and dependencies.</b-link>
        </div>
        <div class="mb-3">
            <b-link href="#" @click="toggleAdvanced">{{ titleAdvanced }}</b-link>
        </div>
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
                <template slot="installed" slot-scope="data">
                    <b-button v-if="!data.value"
                        class="btn-sm"
                        variant="primary"
                        @click="installRepository">
                            Install
                    </b-button>
                    <b-button v-else
                        class="btn-sm"
                        variant="danger"
                        @click="uninstallRepository">
                            Uninstall
                    </b-button>
                </template>
            </b-table>
        </div>
    </b-card>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
export default {
    props: ["repo", "toolSections", "toolshedUrl"],
    data() {
        const galaxy = getGalaxyInstance();
        return {
            toolSection: null,
            toolConfig: null,
            toolConfigs: galaxy.config.tool_configs,
            repoRevision: null,
            repoChecked: "fa fa-check text-success",
            repoUnchecked: "fa fa-times text-danger",
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
            showAdvanced: false,
            loading: true
        };
    },
    computed: {
        titleAdvanced() {
            const prefix = this.showAdvanced ? "Hide" : "Show";
            return `${prefix} advanced installation options.`;
        }
    },
    created() {
        this.toolConfig = this.toolConfigs[0];
        this.services = new Services();
        this.setDetails();
    },
    methods: {
        setDetails() {
            this.services
                .getDetails(this.toolshedUrl, this.repo.id)
                .then(response => {
                    this.repoTable = response;
                    this.setInstalled();
                });
        },
        setInstalled() {
            this.services
                .getInstalled(this.repo)
                .then((revisions) => {
                    this.repoTable.forEach(x => {
                        x.installed = revisions[x.changeset_revision];
                    });
                    window.console.log(revisions);
                    this.loading = false;
                })
                .catch(error => {
                    alert(error);
                });
        },
        toggleAdvanced() {
            this.showAdvanced = !this.showAdvanced;
        },
        installRepository: function(repo) {
            this.services.installRepository(repo);
        },
        uninstallRepository: function(repo) {
            this.services.uninstallRepository(repo);
        }
    }
};
</script>
<style>
.text_align_center {
    text-align: center;
}
</style>
