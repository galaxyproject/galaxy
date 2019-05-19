<template>
    <div class="overflow-auto h-100" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <b-input
                class="mb-3"
                placeholder="search repositories"
                type="text"
                v-model="search"
                @change="load(search)"
            />
            <b-table striped :items="repositories" :fields="fields">
                <template slot="name" slot-scope="row">
                    <b-link href="#" class="font-weight-bold" @click="row.toggleDetails">
                        {{ row.item.name }}
                    </b-link>
                </template>
                <template slot="row-details" slot-scope="row">
                    <b-card>
                        <div class="mb-4">{{ row.item.long_description }}</div>
                        <b-form-group
                            label="Target Section:"
                            description="Choose an existing section in your tool panel to contain the installed tools (optional).">
                            <b-form-input
                                list="sectionLabels"
                                v-model="toolPanelSection"
                            />
                            <datalist id="sectionLabels">
                                <option v-for="section in toolPanelSections">{{ section }}</option>
                            </datalist>
                        </b-form-group>
                        <b-button variant="primary">Install</b-button>
                    </b-card>
                </template>
            </b-table>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";

export default {
    data() {
        return {
            toolshedUrl: "https://toolshed.g2.bx.psu.edu/",
            toolPanelSections: [],
            toolPanelSection: null,
            repositories: [],
            fields: [
                { key: "name" },
                { key: "description" },
                { key: "last_updated", label: "Updated" },
                { key: "repo_owner_username", label: "Owner" },
                { key: "times_downloaded", label: "Downloaded" }
            ],
            page: 1,
            search: "",
            selected: null,
            name: null,
            error: null
        };
    },
    created() {
        this.setToolPanelSections();
        this.load("blast");
    },
    methods: {
        setToolPanelSections() {
            const galaxy = getGalaxyInstance();
            const sections = galaxy.config.toolbox_in_panel;
            this.toolPanelSections = sections.filter(x => x.model_class == "ToolSection")
                                             .map(x => x.name);
        },
        formatCount(value) {
            if (value > 1000)
                return `>${Math.floor(value/1000)}k`;
            return(value);
        },
        load(query) {
            const params = [
                `tool_shed_url=${this.toolshedUrl}`,
                `term=${query}`
            ];
            const url = `${getAppRoot()}api/tool_shed/search?${params.join("&")}`;
            axios
                .get(url)
                .then(response => {
                    this.repositories = response.data.hits.map(x => x.repository);
                    this.repositories.forEach(x => {
                        x.times_downloaded = this.formatCount(x.times_downloaded);
                    });
                    this.error = null;
                })
                .catch(e => {
                    this.error = this._errorMessage(e);
                });
        },
        select: function(repo) {
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
                        this.error = this._errorMessage(e);
                    });
            } else {
                this.error = "This option requires an accessible history.";
            }*/
        },
        _errorMessage: function(e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        },
        onScroll: function({ target: { scrollTop, clientHeight, scrollHeight }}) {
            window.console.log("scrolling");
            if (scrollTop + clientHeight >= scrollHeight) {
                window.console.log("reached");
            }
        }
    }
};
</script>
