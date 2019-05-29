<template>
    <div>
        <div v-if="loading"><span class="fa fa-spinner fa-spin mb-4" /> <span>Loading categories...</span></div>
        <div v-else>
            <div class="m-1 text-muted">
                {{ total }} repositories available at
                <b-link :href="toolshedUrl" target="_blank">{{ toolshedUrl }}</b-link
                >.
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
    props: ["toolshedUrl"],
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
    methods: {
        onCategory(category) {
            this.$emit("onCategory", category);
        }
    }
};
</script>
