<template>
    <div>
        <LoadingSpan v-if="loading" message="Loading categories" />
        <div v-else>
            <GTable :items="categories" :fields="fields">
                <template v-slot:cell(name)="data">
                    <GLink
                        href="#"
                        tooltip
                        title="View repositories in this category"
                        @click.prevent="onCategory(data.item.name)">
                        {{ data.item.name }}
                    </GLink>
                </template>
            </GTable>
        </div>
    </div>
</template>

<script>
import { Services } from "@/components/Toolshed/services";

import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

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
                { key: "description", label: "Description", sortable: false },
                { key: "repositories", label: "Repositories", sortable: true },
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
