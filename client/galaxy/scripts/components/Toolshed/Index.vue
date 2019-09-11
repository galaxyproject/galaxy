<template>
    <div class="overflow-auto h-100 p-1" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <b-input
                class="mb-3"
                placeholder="Search Repositories"
                v-model="queryInput"
                @input="delayQuery"
                @change="setQuery"
            />
            <b-form-radio-group class="mb-3" v-model="tabValue" :options="tabOptions" />
            <div v-if="tabValue">
                <searchlist :query="query" :scrolled="scrolled" @onQuery="setQuery" @onError="setError" />
            </div>
            <div v-else>
                <installedlist :filter="queryInput" />
            </div>
        </div>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import SearchList from "./SearchList/Index.vue";
import InstalledList from "./InstalledList/Index.vue";
export default {
    components: {
        searchlist: SearchList,
        installedlist: InstalledList
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
            error: null,
            tabValue: true,
            tabOptions: [{ text: "Search All", value: true }, { text: "Installed Only", value: false }]
        };
    },
    watch: {
        tabValue() {
            this.queryInput = "";
        }
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
        onScroll: function({ target: { scrollTop, clientHeight, scrollHeight } }) {
            this.scrolled = scrollTop + clientHeight >= scrollHeight;
        }
    }
};
</script>
