<template>
    <b-table striped :items="categories" :fields="fields">
        <template slot="name" slot-scope="data">
            <b-link href="#" class="font-weight-bold" @click="onCategory(data.value)">
                {{ data.value }}
            </b-link>
        </template>
    </b-table>
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
