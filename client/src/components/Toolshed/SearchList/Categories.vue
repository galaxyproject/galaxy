<template>
    <div>
        <LoadingSpan v-if="loading" message="正在加载分类" />
        <b-table v-else striped no-sort-reset :items="categories" :fields="fields">
            <template v-slot:cell(name)="data">
                <b-link
                    href="javascript:void(0)"
                    role="button"
                    class="font-weight-bold"
                    @click="onCategory(data.value)">
                    {{ data.value }}
                </b-link>
            </template>
        </b-table>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import Vue from "vue";

import { Services } from "../services";

Vue.use(BootstrapVue);

export default {
    components: { LoadingSpan },
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
                { key: "name", label: "类别", sortable: true },
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
