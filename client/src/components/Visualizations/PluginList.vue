<template>
    <div class="plugin-list">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <template v-else>
            <DelayedInput
                class="mb-3"
                :value="search"
                :placeholder="titleSearchVisualizations"
                :delay="100"
                @change="onSearch" />
            <div class="plugin-list-items">
                <div v-for="plugin in plugins" :key="plugin.name">
                    <table v-if="match(plugin)">
                        <tr class="plugin-list-item" :data-plugin-name="plugin.name" @click="select(plugin)">
                            <td>
                                <img
                                    v-if="plugin.logo"
                                    alt="ui thumbnails"
                                    class="plugin-list-image"
                                    :src="absPath(plugin.logo)" />
                                <div v-else class="plugin-list-icon fa fa-eye" />
                            </td>
                            <td>
                                <div class="plugin-list-title font-weight-bold">{{ plugin.html }}</div>
                                <div class="plugin-list-text">{{ plugin.description }}</div>
                            </td>
                        </tr>
                        <tr v-if="!fixed">
                            <td />
                            <td v-if="plugin.name == name">
                                <div v-if="hdas && hdas.length > 0">
                                    <div class="font-weight-bold">{{ titleSelectDataset }}</div>
                                    <div class="ui-select">
                                        <select v-model="selected" class="select">
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
                                <div v-else v-localize class="alert alert-danger">
                                    There is no suitable dataset in your current history which can be visualized with
                                    this plugin.
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>
            </div>
        </template>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import axios from "axios";
import DelayedInput from "components/Common/DelayedInput";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import { absPath } from "utils/redirect";

export default {
    components: {
        DelayedInput,
    },
    props: {
        datasetId: {
            type: String,
            default: null,
        },
    },
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
        let url = `${getAppRoot()}api/plugins`;
        if (this.datasetId) {
            this.fixed = true;
            this.selected = this.datasetId;
            url += `?dataset_id=${this.datasetId}`;
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
        absPath,
        onSearch(newValue) {
            this.search = newValue;
        },
        select(plugin) {
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
        create(plugin) {
            this.$router.push(`/visualizations/display?visualization=${plugin.name}&dataset_id=${this.selected}`, {
                title: plugin.name,
            });
        },
        match(plugin) {
            const query = this.search.toLowerCase();
            return (
                !query ||
                plugin.html.toLowerCase().includes(query) ||
                (plugin.description && plugin.description.toLowerCase().includes(query))
            );
        },
        _errorMessage(e) {
            const message = e && e.response && e.response.data && e.response.data.err_msg;
            return message || "Request failed for an unknown reason.";
        },
    },
};
</script>

<style lang="scss" scoped>
@import "theme/blue.scss";
@import "~scss/mixins.scss";

.plugin-list {
    display: flex;
    flex-direction: column;
    height: 100%;

    .plugin-list-items {
        overflow-y: auto;
    }

    .plugin-list-item {
        cursor: pointer;
        .plugin-list-image {
            padding: 1rem;
            width: 5rem;
            height: 4.3rem;
        }
        .plugin-list-icon {
            padding: 1rem;
            width: 5rem;
            height: 4.3rem;
            font-size: 2em;
            text-align: center;
            color: $text-color;
        }
        .plugin-list-text {
            word-break: break-word;
        }
    }
    .plugin-list-item:hover {
        .plugin-list-title {
            text-decoration: underline;
        }
        .plugin-list-text {
            text-decoration: underline;
        }
    }
}
</style>
