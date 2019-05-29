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
            <categories :toolshedUrl="toolshedUrl" @onCategory="setQuery" v-show="queryEmpty" />
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
            queryDelay: 1000,
            queryTimer: null,
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
        setQuery(query) {
            this.clearTimer();
            this.query = this.queryInput = query;
        },
        onScroll: function({ target: { scrollTop, clientHeight, scrollHeight } }) {
            this.scrolled = scrollTop + clientHeight >= scrollHeight;
        }
    }
};
</script>
