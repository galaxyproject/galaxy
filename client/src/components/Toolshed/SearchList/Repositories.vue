<template>
    <div>
        <b-table id="shed-search-results" striped :items="repositories" :fields="fields">
            <template v-slot:cell(name)="row">
                <b-link href="javascript:void(0)" role="button" class="font-weight-bold" @click="row.toggleDetails">
                    {{ row.item.name }}
                </b-link>
                <div>{{ row.item.description }}</div>
            </template>
            <template v-slot:row-details="row">
                <RepositoryDetails :repo="row.item" :toolshed-url="toolshedUrl" />
            </template>
        </b-table>
        <div v-if="noResultsFound" class="unavailable-message">No matching repositories found.</div>
        <loading-span v-if="pageLoading" message="Loading repositories" />
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "../services";
import LoadingSpan from "components/LoadingSpan";
import RepositoryDetails from "../RepositoryDetails/Index.vue";

Vue.use(BootstrapVue);

const READY = 0;
const LOADING = 1;
const COMPLETE = 2;
export default {
    components: {
        LoadingSpan,
        RepositoryDetails,
    },
    props: {
        query: {
            type: String,
            required: true,
        },
        scrolled: {
            type: Boolean,
            required: true,
        },
        toolshedUrl: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            repositories: [],
            fields: [
                { key: "name" },
                { key: "owner", label: "Owner" },
                { key: "times_downloaded", label: "Downloaded" },
                { key: "last_updated", label: "Updated" },
            ],
            page: 1,
            pageSize: 50,
            pageState: READY,
            error: null,
        };
    },
    computed: {
        pageLoading() {
            return this.pageState === LOADING;
        },
        noResultsFound() {
            return this.repositories.length === 0 && !this.pageLoading;
        },
    },
    watch: {
        toolshedUrl() {
            this.load();
        },
        query() {
            this.load();
        },
        scrolled() {
            if (this.scrolled && this.pageState === READY) {
                this.load(this.page + 1);
            }
        },
    },
    created() {
        this.services = new Services();
        this.load();
    },
    methods: {
        load(page = 1) {
            this.page = page;
            this.pageState = LOADING;
            if (page == 1) {
                this.repositories = [];
            }
            this.services
                .getRepositories({
                    tool_shed_url: this.toolshedUrl,
                    q: this.query,
                    page: this.page,
                    page_size: this.pageSize,
                })
                .then((incoming) => {
                    this.repositories = this.repositories.concat(incoming);
                    if (incoming.length < this.pageSize) {
                        this.pageState = COMPLETE;
                    } else {
                        this.pageState = READY;
                    }
                })
                .catch((errorMessage) => {
                    this.$emit("onError", errorMessage);
                });
        },
    },
};
</script>
