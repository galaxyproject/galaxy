<template>
    <div class="overflow-auto h-100 p-1" @scroll="onScroll">
        <b-input-group class="mb-3">
            <b-input
                placeholder="search repositories"
                v-model="queryInput"
                @input="delayQuery"
                @change="setQuery"
                @keydown.esc="setQuery()"
            />
            <b-input-group-append v-b-tooltip.hover title="clear search (esc)">
                <b-btn @click="setQuery()">
                    <i class="fa fa-times" />
                </b-btn>
            </b-input-group-append>
        </b-input-group>
        <serverselection
            :toolshedUrl="toolshedUrl"
            :toolshedUrls="toolshedUrls"
            :total="total"
            :loading="loading"
            @onToolshed="setToolshed"
        />
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <repositories
                :query="query"
                :scrolled="scrolled"
                :toolshedUrl="toolshedUrl"
                @onError="setError"
                v-if="!queryEmpty"
            />
            <categories
                :toolshedUrl="toolshedUrl"
                :loading="loading"
                @onCategory="setQuery"
                @onTotal="setTotal"
                @onError="setError"
                @onLoading="setLoading"
                v-show="queryEmpty"
            />
        </div>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import Categories from "./Categories.vue";
import Repositories from "./Repositories.vue";
import ServerSelection from "./ServerSelection.vue";
export default {
    components: {
        categories: Categories,
        repositories: Repositories,
        serverselection: ServerSelection
    },
    data() {
        return {
            toolshedUrl: null,
            toolshedUrls: [],
            queryInput: null,
            queryDelay: 1000,
            queryTimer: null,
            queryLength: 3,
            query: null,
            scrolled: false,
            loading: false,
            total: 0,
            error: null
        };
    },
    created() {
        this.configureToolsheds();
    },
    computed: {
        queryEmpty() {
            return !this.query || this.query.length < this.queryLength;
        }
    },
    methods: {
        configureToolsheds() {
            const galaxy = getGalaxyInstance();
            this.toolshedUrls = galaxy.config.tool_shed_urls;
            if (!this.toolshedUrls || this.toolshedUrls.length == 0) {
                this.setError("Toolshed registry is empty, no servers found.");
            } else {
                this.toolshedUrl = this.toolshedUrls[0];
            }
        },
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
            this.error = null;
            this.toolshedUrl = url;
        },
        setTotal(total) {
            this.total = total;
        },
        setLoading(loading) {
            this.loading = loading;
        },
        onScroll({ target: { scrollTop, clientHeight, scrollHeight } }) {
            this.scrolled = scrollTop + clientHeight >= scrollHeight;
        }
    }
};
</script>
