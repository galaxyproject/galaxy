<template>
    <div>
        <b-table striped :items="repositories" :fields="fields">
            <template v-slot:cell(name)="row">
                <b-link href="javascript:void(0)" role="button" class="font-weight-bold" @click="row.toggleDetails">
                    {{ row.item.name }}
                </b-link>
                <p>{{ row.item.description }}</p>
            </template>
            <template v-slot:row-details="row">
                <RepositoryDetails :repo="row.item" :toolshedUrl="toolshedUrl" />
            </template>
        </b-table>
        <div class="unavailable-message" v-if="noResultsFound">
            No matching repositories found.
        </div>
        <div v-if="pageLoading">
            <span class="fa fa-spinner fa-spin mb-4" />
            <span class="loading-message">Loading repositories...</span>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "../services.js";
import RepositoryDetails from "../RepositoryDetails/Index.vue";

Vue.use(BootstrapVue);

const READY = 0;
const LOADING = 1;
const COMPLETE = 2;
export default {
    components: {
        RepositoryDetails
    },
    props: ["query", "scrolled", "toolshedUrl"],
    data() {
        return {
            repositories: [],
            fields: [
                { key: "name" },
                { key: "owner", label: "Owner" },
                { key: "times_downloaded", label: "Downloaded" },
                { key: "last_updated", label: "Updated" }
            ],
            page: 1,
            pageSize: 50,
            pageState: READY,
            error: null
        };
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
        }
    },
    computed: {
        pageLoading() {
            return this.pageState === LOADING;
        },
        noResultsFound() {
            return this.repositories.length === 0 && !this.pageLoading;
        }
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
                    page_size: this.pageSize
                })
                .then(incoming => {
                    this.repositories = this.repositories.concat(incoming);
                    if (incoming.length < this.pageSize) {
                        this.pageState = COMPLETE;
                    } else {
                        this.pageState = READY;
                    }
                })
                .catch(errorMessage => {
                    this.$emit("onError", errorMessage);
                });
        }
    }
};
</script>
