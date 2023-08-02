<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading categories" />
        <GTable v-else :fields="fields" :items="categories" no-sort-reset striped>
            <template v-slot:cell(name)="data">
                <GLink href="javascript:void(0)" role="button" class="font-weight-bold" @click="onCategory(data.value)">
                    {{ data.value }}
                </GLink>
            </template>
        </GTable>
    </div>
</template>
<script>
import LoadingSpan from "components/LoadingSpan";

import { GLink, GTable } from "@/component-library";

import { Services } from "../services";

export default {
    components: {
        GLink,
        GTable,
        LoadingSpan,
    },
    props: {
        toolshedUrl: {
            type: String,
            required: true,
        },
        loading: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            categories: [],
            fields: [
                { key: "name", label: "Category", sortable: true },
                { key: "description", sortable: false },
                { key: "repositories", sortable: true },
            ],
        };
    },
    watch: {
        toolshedUrl() {
            this.load();
        },
    },
    created() {
        this.services = new Services();
        this.load();
    },
    methods: {
        load() {
            this.$emit("onLoading", true);
            this.services
                .getCategories(this.toolshedUrl)
                .then((categories) => {
                    this.categories = categories;
                    const reducer = (value, entry) => value + entry.repositories;
                    this.$emit("onTotal", this.categories.reduce(reducer, 0));
                    this.$emit("onLoading", false);
                })
                .catch((errorMessage) => {
                    this.$emit("onError", errorMessage);
                    this.$emit("onLoading", false);
                });
        },
        onCategory(category) {
            this.$emit("onCategory", `category:'${category}'`);
        },
    },
};
</script>
