<template>
    <div class="overflow-auto h-100" @scroll="onScroll">
        <div v-if="error" class="alert alert-danger">{{ error }}</div>
        <div v-else>
            <b-input class="mb-3" placeholder="search repositories" type="text" v-model="query" @change="load()" />
            <b-table striped :items="repositories" :fields="fields">
                <template slot="name" slot-scope="row">
                    <b-link href="#" class="font-weight-bold" @click="row.toggleDetails">
                        {{ row.item.name }}
                    </b-link>
                </template>
                <template slot="row-details" slot-scope="row">
                    <repositoryoptions :repo="row.item" :toolSections="toolSections"/>
                </template>
            </b-table>
            <div v-if="noResultsFound">
                No matching repositories found.
            </div>
            <div v-if="pageLoading">
                <span class="fa fa-spinner fa-spin mb-4" /> <span>Loading repositories...</span>
            </div>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import RepositoryOptions from "./RepositoryOptions.vue";
import { Services } from "./services.js";
import axios from "axios";
const READY = 0;
const LOADING = 1;
const COMPLETE = 2;
export default {
    components: {
        repositoryoptions: RepositoryOptions
    },
    data() {
        return {
            toolshedUrl: "https://toolshed.g2.bx.psu.edu/",
            toolSections: [],
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
            query: null,
            error: null
        };
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
        this.setToolSections();
        this.query = "blast";
        this.load();
    },
    methods: {
        setToolSections() {
            const galaxy = getGalaxyInstance();
            const sections = galaxy.config.toolbox_in_panel;
            this.toolSections = sections.filter(x => x.model_class == "ToolSection").map(x => x.name);
        },
        load(page = 1) {
            this.page = page;
            this.pageState = LOADING;
            const params = [
                `tool_shed_url=${this.toolshedUrl}`,
                `q=${this.query}`,
                `page=${this.page}`,
                `page_size=${this.pageSize}`
            ];
            this.services
                .getRepositories(params)
                .then(incoming => {
                    if (this.page === 1) {
                    this.repositories = incoming;
                    } else {
                        this.repositories = this.repositories.concat(incoming);
                    }
                    if (incoming.length < this.pageSize) {
                        this.pageState = COMPLETE;
                    } else {
                        this.pageState = READY;
                    }
                    this.error = null;
                })
                .catch(errorMessage => {
                    this.error = errorMessage;
                });
        },
        onScroll: function({ target: { scrollTop, clientHeight, scrollHeight } }) {
            if (scrollTop + clientHeight >= scrollHeight) {
                if (this.pageState === READY) {
                    this.load(this.page + 1);
                }
            }
        }
    }
};
</script>
