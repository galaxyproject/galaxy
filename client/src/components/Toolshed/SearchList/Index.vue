<template>
    <div>
        <ServerSelection
            :toolshed-url="toolshedUrl"
            :toolshed-urls="toolshedUrls"
            :total="total"
            :loading="loading"
            @onToolshed="setToolshed" />
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <Repositories
                v-if="!queryEmpty"
                :query="query"
                :scrolled="scrolled"
                :toolshed-url="toolshedUrl"
                @onError="setError" />
            <Categories
                v-show="queryEmpty"
                :toolshed-url="toolshedUrl"
                :loading="loading"
                @onCategory="setQuery"
                @onTotal="setTotal"
                @onError="setError"
                @onLoading="setLoading" />
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
        Categories,
        Repositories,
        ServerSelection,
    },
    props: {
        query: {
            type: String,
            default: null,
        },
        scrolled: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            toolshedUrl: null,
            toolshedUrls: [],
            queryLength: 3,
            loading: false,
            total: 0,
            error: null,
            tabCurrent: "true",
            tabOptions: [
                { text: "搜索全部", value: true },
                { text: "仅已安装", value: false },
            ],
        };
    },
    computed: {
        queryEmpty() {
            return !this.query || this.query.length < this.queryLength;
        },
    },
    created() {
        this.configureToolsheds();
    },
    methods: {
        configureToolsheds() {
            const galaxy = getGalaxyInstance();
            this.toolshedUrls = galaxy.config.tool_shed_urls;
            if (!this.toolshedUrls || this.toolshedUrls.length == 0) {
                this.setError("工具库注册表为空，未找到服务器。");
            } else {
                this.toolshedUrl = this.toolshedUrls[0];
            }
        },
        setError(error) {
            this.error = error;
        },
        setQuery(query) {
            this.$emit("onQuery", query);
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
    },
};
</script>
