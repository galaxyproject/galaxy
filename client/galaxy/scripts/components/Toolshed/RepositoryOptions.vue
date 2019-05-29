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
                    <b-form-select :options="revisions" v-model="revision" />
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
        <b-button variant="primary" @click="installRepository(repo)">Install</b-button>
        <b-button variant="danger" @click="uninstallRepository(repo)">Uninstall</b-button>
    </b-card>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
export default {
    props: ["repo", "toolSections"],
    data() {
        const galaxy = getGalaxyInstance();
        return {
            toolSection: null,
            toolConfig: null,
            toolConfigs: galaxy.config.tool_configs,
            repoRevisions: [],
            showAdvanced: false
        };
    },
    computed: {
        titleAdvanced() {
            const prefix = this.showAdvanced ? "Hide" : "Show";
            return `${prefix} advanced installation options.`;
        }
    },
    methods: {
        toggleAdvanced() {
            this.showAdvanced = !this.showAdvanced;
        },
        installRepository: function(repo) {
            window.console.log(repo);
            /*const Galaxy = getGalaxyInstance();
            const history_id = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
            if (history_id) {
                axios
                    .get(`${getAppRoot()}api/repositories/${plugin.name}?history_id=${history_id}`)
                    .then(response => {
                        this.name = plugin.name;
                        this.hdas = response.data && response.data.hdas;
                        if (this.hdas && this.hdas.length > 0) {
                            this.selected = this.hdas[0].id;
                        }
                    })
                    .catch(e => {
                        this.error = this.setErrorMessage(e);
                    });
            } else {
                this.error = "This option requires an accessible history.";
            }*/
        },
        uninstallRepository: function(repo) {}
    }
};
</script>
