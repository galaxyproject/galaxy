<template>
    <DependencyIndexWrapper
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
                <GButton @click="deleteSelected"> Delete Selected Environments </GButton>
            </div>
        </template>
    </DependencyIndexWrapper>
</template>
<script>
import { deletedUnusedPaths, getDependencyUnusedPaths } from "../AdminServices";
import DependencyIndexWrapper from "./DependencyIndexWrapper";

import GButton from "@/components/BaseComponents/GButton.vue";

export default {
    components: { DependencyIndexWrapper, GButton },
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
