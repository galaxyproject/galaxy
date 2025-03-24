<template>
    <div class="overflow-auto h-100 p-1" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <b-input-group class="mb-3">
                <b-input
                    id="toolshed-repo-search"
                    v-model="queryInput"
                    placeholder="搜索仓库"
                    @input="delayQuery"
                    @change="setQuery"
                    @keydown.esc="setQuery()" />
                <b-input-group-append v-b-tooltip.hover :title="titleClearSearch">
                    <b-btn @click="setQuery()">
                        <i class="fa fa-times" />
                    </b-btn>
                </b-input-group-append>
            </b-input-group>
            <b-form-radio-group v-model="tabValue" class="mb-3" :options="tabOptions" />
            <div v-if="tabValue">
                <SearchList :query="query" :scrolled="scrolled" @onQuery="setQuery" @onError="setError" />
            </div>
            <div v-else>
                <InstalledList :filter="queryInput" @onQuery="setQuery" />
            </div>
        </div>
    </div>
</template>
<script>
import _l from "utils/localization";

import InstalledList from "./InstalledList/Index.vue";
import SearchList from "./SearchList/Index.vue";

export default {
    components: {
        SearchList,
        InstalledList,
    },
    data() {
        return {
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
            tabOptions: [
                { text: "搜索全部", value: true },
                { text: "仅已安装", value: false },
            ],
            titleClearSearch: _l("清除搜索(esc)"),
        };
    },
    computed: {
        queryEmpty() {
            return !this.query || this.query.length < this.queryLength;
        },
    },
    watch: {
        tabValue() {
            this.setQuery("");
        },
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
        onScroll({ target: { scrollTop, clientHeight, scrollHeight } }) {
            this.scrolled = scrollTop + clientHeight >= scrollHeight;
        },
    },
};
</script>
