<template>
    <div>
        <div v-if="loading"><span class="fa fa-spinner fa-spin mb-4" /> <span>Loading categories...</span></div>
        <div v-else>
            <div class="m-1 text-muted">
                {{ total }} repositories available at
                <span class="dropdown">
                    <b-link id="dropdownToolshedUrl" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                        {{ toolshedUrl }}
                    </b-link>
                    <div class="dropdown-menu" aria-labelledby="dropdownToolshedUrl">
                        <a v-for="url in toolshedUrls" class="dropdown-item" href="#" @click="onToolshed(url)">{{
                            url
                        }}</a>
                    </div>
                </span>
            </div>
            <b-table striped :items="categories" :fields="fields">
                <template slot="name" slot-scope="data">
                    <b-link href="#" class="font-weight-bold" @click="onCategory(data.value)">
                        {{ data.value }}
                    </b-link>
                </template>
            </b-table>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "./services.js";
export default {
    props: ["toolshedUrl", "toolshedUrls"],
    data() {
        return {
            categories: [],
            total: 0,
            loading: true,
            fields: {
                name: {
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
            this.loading = true;
            this.services
                .getCategories(this.toolshedUrl)
                .then(categories => {
                    this.categories = categories;
                    this.total = this.categories.reduce((value, entry) => value + entry.repositories, 0);
                    this.loading = false;
                })
                .catch(errorMessage => {
                    alert(errorMessage);
                });
        },
        onCategory(category) {
            this.$emit("onCategory", category);
        },
        onToolshed(url) {
            this.$emit("onToolshed", url);
        }
    }
};
</script>
