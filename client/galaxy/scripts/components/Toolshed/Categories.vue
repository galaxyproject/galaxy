<template>
    <b-table striped :items="categories" :fields="fields"/>
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
            fields: ["name", "description", "repositories"]
        };
    },
    created() {
        this.services = new Services();
        this.services
            .getCategories(this.toolshedUrl)
            .then(categories => {
                this.categories = categories;
                window.console.log(categories);
            })
            .catch(errorMessage => {
                alert(errorMessage);
            });
    }
};
</script>
