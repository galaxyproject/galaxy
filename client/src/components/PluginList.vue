<template>
    <div class="ui-thumbnails">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <div class="search-input">
                <input
                    class="search-query parent-width"
                    name="query"
                    :placeholder="titleSearchVisualizations"
                    autocomplete="off"
                    type="text"
                    v-model="search" />
            </div>
            <div v-for="plugin in plugins" :key="plugin.name">
                <table v-if="match(plugin)">
                    <tr class="ui-thumbnails-item" @click="select(plugin)">
                        <td>
                            <img
                                v-if="plugin.logo"
                                alt="ui thumbnails"
                                class="ui-thumbnails-image"
                                :src="plugin.logo" />
                            <div v-else class="ui-thumbnails-icon fa fa-eye" />
                        </td>
                        <td>
                            <div class="ui-thumbnails-title font-weight-bold">{{ plugin.html }}</div>
                            <div class="ui-thumbnails-text">{{ plugin.description }}</div>
                        </td>
                    </tr>
                    <tr v-if="!fixed">
                        <td />
                        <td v-if="plugin.name == name">
                            <div v-if="hdas && hdas.length > 0">
                                <div class="font-weight-bold">{{ titleSelectDataset }}</div>
                                <div class="ui-select">
                                    <select class="select" v-model="selected">
                                        <option v-for="file in hdas" :key="file.id" :value="file.id">
                                            {{ file.name }}
                                        </option>
                                    </select>
                                    <div class="icon-dropdown fa fa-caret-down" />
                                </div>
                                <button
                                    type="button"
                                    class="ui-button-default float-left mt-3 btn btn-primary"
                                    @click="create(plugin)">
                                    <i class="icon fa fa-check" />
                                    <span class="title">{{ titleCreateVisualization }}</span>
                                </button>
                            </div>
                            <div v-else class="alert alert-danger" v-localize>
                                There is no suitable dataset in your current history which can be visualized with this
                                plugin.
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</template>
<script>
import $ from "jquery";
import _l from "utils/localization";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";

export default {
    data() {
        return {
            plugins: [],
            hdas: [],
            search: "",
            selected: null,
            name: null,
            error: null,
            fixed: false,
            titleSearchVisualizations: _l("search visualizations"),
            titleCreateVisualization: _l("Create Visualization"),
            titleSelectDataset: _l("Select a dataset to visualize:"),
        };
    },
    created() {
        const Galaxy = getGalaxyInstance();
        let url = `${getAppRoot()}api/plugins`;
        const dataset_id = Galaxy.params.dataset_id;
        if (dataset_id) {
            this.fixed = true;
            this.selected = dataset_id;
            url += `?dataset_id=${dataset_id}`;
        }
        axios
            .get(url)
            .then((response) => {
                this.plugins = response.data;
            })
            .catch((e) => {
                this.error = this._errorMessage(e);
            });
    },
    methods: {
        select: function (plugin) {
            if (this.fixed) {
                this.create(plugin);
            } else {
                const Galaxy = getGalaxyInstance();
                const history_id = Galaxy.currHistoryPanel && Galaxy.currHistoryPanel.model.id;
                if (history_id) {
                    axios
                        .get(`${getAppRoot()}api/plugins/${plugin.name}?history_id=${history_id}`)
                        .then((response) => {
                            this.name = plugin.name;
                            this.hdas = response.data && response.data.hdas;
                            if (this.hdas && this.hdas.length > 0) {
                                this.selected = this.hdas[0].id;
                            }
                        })
                        .catch((e) => {
                            this.error = this._errorMessage(e);
                        });
                } else {
                    this.error = "This option requires an accessible history.";
                }
            }
        },
        create: function (plugin) {
            const href = `${plugin.href}?dataset_id=${this.selected}`;
            if (plugin.target == "_top") {
                window.location.href = href;
            } else {
                $("#galaxy_main").attr("src", href);
            }
        },
        match: function (plugin) {
            return (
                !this.search ||
                plugin.name.indexOf(this.search) != -1 ||
                (plugin.description && plugin.description.indexOf(this.search) != -1)
            );
        },
        _errorMessage: function (e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        },
    },
};
</script>
