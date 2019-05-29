<template>
    <div class="overflow-auto h-100" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <b-input class="mb-3" placeholder="search repositories" type="text" v-model="queryInput" @change="changeQuery" />
            <repositories :query="query" :scrolled="scrolled" :toolshedUrl="toolshedUrl" v-if="!queryEmpty" />
            <categories :toolshedUrl="toolshedUrl" @onCategory="changeQuery" v-show="queryEmpty" />
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import Categories from "./Categories.vue";
import Repositories from "./Repositories.vue";
export default {
    components: {
        categories: Categories,
        repositories: Repositories
    },
    data() {
        return {
            toolshedUrl: "https://toolshed.g2.bx.psu.edu/",
            queryInput: null,
            query: null,
            scrolled: false,
            error: null
        };
    },
    computed: {
        queryEmpty() {
            return !this.query;
        }
    },
    methods: {
        changeQuery(query) {
            this.query = this.queryInput = query;
        },
        onScroll: function({ target: { scrollTop, clientHeight, scrollHeight } }) {
            this.scrolled = scrollTop + clientHeight >= scrollHeight;
        }
    }
};
</script>
