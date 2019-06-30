<template>
    <div>
        <div v-if="loading">
            <span class="fa fa-spinner fa-spin mb-4 mr-1" />
            <span>Loading categories...</span>
        </div>
        <b-table v-else striped :items="categories" :fields="fields">
            <template slot="name" slot-scope="data">
                <b-link href="#" class="font-weight-bold" @click="onCategory(data.value)">
                    {{ data.value }}
                </b-link>
            </template>
        </b-table>
    </div>
</template>
<script>
import { Services } from "./services.js";
export default {
    props: ["toolshedUrl", "loading"],
    data() {
        return {
            categories: [],
            fields: {
                name: {
                    label: "Category",
                    sortable: true
                },
                description: {
                    sortable: false
                },
                repositories: {
                    sortable: true
                }
            }
        };
    },
    created() {
        this.services = new Services();
        this.load();
    },
    watch: {
        toolshedUrl() {
            this.load();
        }
    },
    methods: {
        load() {
            this.$emit("onLoading", true);
            this.services
                .getCategories(this.toolshedUrl)
                .then(categories => {
                    this.categories = categories;
                    const reducer = (value, entry) => value + entry.repositories;
                    this.$emit("onTotal", this.categories.reduce(reducer, 0));
                    this.$emit("onLoading", false);
                })
                .catch(errorMessage => {
                    this.$emit("onError", errorMessage);
                    this.$emit("onLoading", false);
                });
        },
        onCategory(category) {
            this.$emit("onCategory", category);
        }
    }
};
</script>
