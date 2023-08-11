<template>
    <DependencyIndexWrapper
        :loading="loading"
        :error="error"
        loading-message="Loading tool dependency resolver information">
        <template v-slot:body>
            <GTable id="unused-paths-table" :fields="fields" :items="items" striped>
                <template v-slot:cell(selected)="data">
                    <GFormCheckbox v-model="data.item.selected" />
                </template>
            </GTable>
        </template>
        <template v-slot:actions>
            <div>
                <GButton @click="deleteSelected"> Delete Selected Environments </GButton>
            </div>
        </template>
    </DependencyIndexWrapper>
</template>
<script>
import { GButton, GFormCheckbox, GTable } from "@/component-library";

import { deletedUnusedPaths, getDependencyUnusedPaths } from "../AdminServices";
import DependencyIndexWrapper from "./DependencyIndexWrapper";

export default {
    components: {
        DependencyIndexWrapper,
        GButton,
        GFormCheckbox,
        GTable,
    },
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
