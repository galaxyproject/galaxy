<template>
    <div class="ui-thumbnails">
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
                        Details
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
            repositories: [],
            fields: ["name", "description", "last_updated", "repo_owner_username", "times_downloaded"],
            search: "",
            selected: null,
            name: null,
            error: null
        };
    },
    created() {
        this.load("blast");
    },
    methods: {
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
                    this.error = null;
                    window.console.log(this.repositories);
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
        match: function(plugin) {
            return (
                !this.search ||
                plugin.name.indexOf(this.search) != -1 ||
                (plugin.description && plugin.description.indexOf(this.search) != -1)
            );
        },
        _errorMessage: function(e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        }
    }
};
</script>
