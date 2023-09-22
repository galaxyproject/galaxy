<template>
    <dependency-index-wrapper
        :loading="loading"
        :error="error"
        loading-message="Loading tool dependency resolver information">
        <template v-slot:body>
            <b-table id="unused-paths-table" striped :fields="fields" :items="items">
                <template v-slot:cell(selected)="data">
                    <b-form-checkbox v-model="data.item.selected"></b-form-checkbox>
                </template>
            </b-table>
        </template>
        <template v-slot:actions>
            <div>
                <b-button @click="deleteSelected"> Delete Selected Environments </b-button>
            </div>
        </template>
    </dependency-index-wrapper>
</template>
<script>
import DependencyIndexWrapper from "./DependencyIndexWrapper";
import { getDependencyUnusedPaths, deletedUnusedPaths } from "../AdminServices";

export default {
    components: { DependencyIndexWrapper },
    data() {
        return {
            error: null,
            loading: true,
            fields: [{ key: "selected", label: "" }, { key: "path" }],
            paths: [],
        };
    },
    computed: {
        items: function () {
            return this.paths.map((path) => {
                return { path: path, selected: false, _showDetails: false };
            });
        },
        hasSelectedPaths: function () {
            for (const item of this.items) {
                if (item["selected"]) {
                    return true;
                }
            }
            return false;
        },
    },
    created: function () {
        this.load();
    },
    methods: {
        load() {
            getDependencyUnusedPaths()
                .then((response) => {
                    this.paths = response;
                    this.loading = false;
                })
                .catch(this.handleError);
        },
        deleteSelected() {
            const paths = [];
            for (const item of this.items) {
                if (item["selected"]) {
                    paths.push(item["path"]);
                }
            }
            this.loading = true;
            deletedUnusedPaths(paths)
                .then(() => {
                    this.load();
                })
                .catch(this.handleError);
        },
        handleError(e) {
            this.error = e;
        },
    },
};
</script>
