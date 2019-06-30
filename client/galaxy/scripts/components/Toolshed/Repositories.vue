<template>
    <div>
        <b-table striped :items="repositories" :fields="fields">
            <template slot="name" slot-scope="row">
                <b-link href="#" class="font-weight-bold" @click="row.toggleDetails">
                    {{ row.item.name }}
                </b-link>
            </template>
            <template slot="row-details" slot-scope="row">
                <repositorydetails :repo="row.item" :toolshedUrl="toolshedUrl" />
            </template>
        </b-table>
        <div v-if="noResultsFound">
            No matching repositories found.
        </div>
        <div v-if="pageLoading">
            <span class="fa fa-spinner fa-spin mb-4" />
            <span>Loading repositories...</span>
        </div>
    </div>
</template>
<script>
import RepositoryDetails from "./RepositoryDetails.vue";
import { Services } from "./services.js";
const READY = 0;
const LOADING = 1;
const COMPLETE = 2;
export default {
    components: {
        repositorydetails: RepositoryDetails
    },
    props: ["query", "scrolled", "toolshedUrl"],
    data() {
        return {
            repositories: [],
            fields: [
                { key: "name" },
                { key: "description" },
                { key: "last_updated", label: "Updated" },
                { key: "repo_owner_username", label: "Owner" },
                { key: "times_downloaded", label: "Downloaded" }
            ],
            page: 1,
            pageSize: 10,
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
