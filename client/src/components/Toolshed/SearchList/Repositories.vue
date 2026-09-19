<template>
    <div>
        <div v-if="noResultsFound" class="unavailable-message">No matching repositories found.</div>

        <LoadingSpan v-if="pageLoading" message="Loading repositories" />
        <GTable v-else id="shed-search-results" :items="repositories" :fields="fields">
            <template v-slot:cell(name)="{ item, toggleDetails }">
                <GLink href="#" @click.prevent="toggleDetails">{{ item.name }}</GLink>
                <div>{{ item.description }}</div>
            </template>
            <template v-slot:row-details="{ item }">
                <RepositoryDetails :repo="item" :toolshed-url="toolshedUrl" />
            </template>
        </GTable>
    </div>
</template>

<script>
import { Services } from "../services";

import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import RepositoryDetails from "@/components/Toolshed/RepositoryDetails/Index.vue";

const READY = 0;
const LOADING = 1;
const COMPLETE = 2;
export default {
    components: {
        LoadingSpan,
        GLink,
        GTable,
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
                { key: "name", label: "Name", sortable: true },
                { key: "owner", label: "Owner", sortable: true },
                { key: "times_downloaded", label: "Downloaded", sortable: true },
                { key: "last_updated", label: "Updated", sortable: true },
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
