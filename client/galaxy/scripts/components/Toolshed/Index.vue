<template>
    <div class="overflow-auto h-100 p-1" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <b-input
                class="mb-3"
                placeholder="search repositories"
                v-model="queryInput"
                @input="delayQuery"
                @change="setQuery"
            />
            <repositories :query="query" :scrolled="scrolled" :toolshedUrl="toolshedUrl" v-if="!queryEmpty" />
            <categories
                :toolshedUrl="toolshedUrl"
                :toolshedUrls="toolshedUrls"
                @onToolshed="setToolshed"
                @onCategory="setQuery"
                @onError="setError"
                v-show="queryEmpty"
            />
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
            toolshedUrl: null,
            toolshedUrls: ["https://toolshed.g2.bx.psu.edu/", "https://testtoolshed.g2.bx.psu.edu"],
            queryInput: null,
            queryDelay: 1000,
            queryTimer: null,
            query: null,
            scrolled: false,
            error: null
        };
    },
    created() {
        this.toolshedUrl = this.toolshedUrls[0];
    },
    computed: {
        queryEmpty() {
            return !this.query;
        }
    },
    methods: {
        clearTimer() {
            if (this.queryTimer) {
                clearTimeout(this.queryTimer);
            }
        },
        delayQuery(query) {
            this.clearTimer();
            if (query) {
                this.queryTimer = setTimeout(() => {
                    this.setQuery(query);
                }, this.queryDelay);
            } else {
                this.setQuery(query);
            }
        },
        setError(error) {
            this.error = error;
        },
        setQuery(query) {
            this.clearTimer();
            this.query = this.queryInput = query;
        },
        setToolshed(url) {
            this.toolshedUrl = url;
        },
        onScroll: function({ target: { scrollTop, clientHeight, scrollHeight } }) {
            this.scrolled = scrollTop + clientHeight >= scrollHeight;
        }
    }
};
</script>
