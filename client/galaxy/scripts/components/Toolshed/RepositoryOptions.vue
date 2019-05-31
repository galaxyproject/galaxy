<template>
    <b-card>
        <div class="mb-1">{{ repo.long_description }}</div>
        <div class="mb-1">
            <b-link :href="repo.repository_url" target="_blank">Show additional details and dependencies.</b-link>
        </div>
        <div class="mb-3">
            <b-link href="#" @click="toggleAdvanced">{{ titleAdvanced }}</b-link>
        </div>
        <div v-if="showAdvanced">
            <b-form-group label="Available Revisions:" description="Choose an repository revision configuration.">
                <div class="ui-select">
                    <b-form-select :options="repoRevisions" v-model="repoRevision" />
                </div>
            </b-form-group>
            <b-form-group
                label="Target Section:"
                description="Choose an existing section in your tool panel to contain the installed tools (optional)."
            >
                <b-form-input list="sectionLabels" v-model="toolSection" />
                <datalist id="sectionLabels">
                    <option v-for="section in toolSections">{{ section }}</option>
                </datalist>
            </b-form-group>
            <b-form-group label="Tool Configuration:" description="Choose an tool configuration.">
                <div class="ui-select">
                    <b-form-select :options="toolConfigs" v-model="toolConfig" />
                </div>
            </b-form-group>
        </div>
        <div v-if="loading">
            <span class="fa fa-spinner fa-spin" />
        </div>
        <div v-else>
            <b-button v-if="!repoInstalled" variant="primary" @click="installRepository">Install</b-button>
            <b-button v-else variant="danger" @click="uninstallRepository">Uninstall</b-button>
        </div>
    </b-card>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import { Services } from "./services.js";
export default {
    props: ["repo", "toolSections"],
    data() {
        const galaxy = getGalaxyInstance();
        return {
            toolSection: null,
            toolConfig: null,
            toolConfigs: galaxy.config.tool_configs,
            repoRevision: null,
            repoRevisions: ["01b38f20197e", "01b38f20197d", "01b38f20197c"],
            showAdvanced: false,
            loading: true
        };
    },
    computed: {
        titleAdvanced() {
            const prefix = this.showAdvanced ? "Hide" : "Show";
            return `${prefix} advanced installation options.`;
        },
        repoInstalled() {
            return this.installedRevisions[this.repoRevision];
        }
    },
    created() {
        this.repoRevision = this.repoRevisions[0];
        this.toolConfig = this.toolConfigs[0];
        this.getInstalledRevisions();
    },
    methods: {
        getInstalledRevisions() {
            this.services = new Services();
            this.services
                .getInstalledRevisions(this.repo)
                .then((revisions) => {
                    this.installedRevisions = {"01b38f20197e": true, "01b38f20197c": true};
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
