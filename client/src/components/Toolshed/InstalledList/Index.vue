<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <LoadingSpan v-if="loading" message="Loading installed repositories" />
            <div v-else>
                <GAlert :variant="messageVariant" :show="showMessage">{{ message }}</GAlert>
                <div class="m-1">
                    <span class="installed-message text-muted">
                        {{ repositories.length }} repositories installed on this instance.
                    </span>
                    <GLink class="font-weight-bold" @click="toggleMonitor">
                        <span v-if="showMonitor">
                            <span class="fa fa-angle-double-up" />
                            <span>Hide installation progress.</span>
                        </span>
                        <span v-else>
                            <span class="fa fa-angle-double-down" />
                            <span>Show installation progress.</span>
                        </span>
                    </GLink>
                </div>
                <Monitor v-if="showMonitor" @onQuery="onQuery" />
                <GTable
                    id="repository-table"
                    striped
                    :fields="fields"
                    :sort-by="sortBy"
                    :items="repositories"
                    :filter="filter"
                    @filtered="filtered">
                    <template v-slot:cell(name)="row">
                        <GLink href="#" role="button" class="font-weight-bold" @click="row.toggleDetails">
                            <div v-if="!isLatest(row.item)">
                                <GBadge variant="danger" class="mb-2"> Newer version available! </GBadge>
                            </div>
                            <div class="name">{{ row.item.name }}</div>
                        </GLink>
                        <div>{{ row.item.description }}</div>
                    </template>
                    <template v-slot:row-details="row">
                        <RepositoryDetails :repo="row.item" />
                    </template>
                </GTable>
                <div v-if="showNotFound">
                    No matching entries found for: <span class="font-weight-bold">{{ filter }}</span
                    >.
                </div>
                <div v-if="showNotAvailable">No installed repositories found.</div>
            </div>
        </div>
    </div>
</template>
<script>
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";

import { GAlert, GBadge, GLink, GTable } from "@/component-library";

import { Services } from "../services";
import RepositoryDetails from "./Details";
import Monitor from "./Monitor";

export default {
    components: {
        GAlert,
        GBadge,
        GLink,
        GTable,
        LoadingSpan,
        Monitor,
        RepositoryDetails,
    },
    props: {
        filter: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            error: null,
            loading: true,
            message: null,
            messageVariant: null,
            nRepositories: 0,
            repositories: [],
            showMonitor: false,
            sortBy: "name",
        };
    },
    computed: {
        showNotFound() {
            return this.nRepositories === 0 && this.filter;
        },
        showNotAvailable() {
            return this.nRepositories === 0 && !this.filter;
        },
        showMessage() {
            return !!this.message;
        },
        numToolsheds() {
            const toolsheds = new Set();
            this.repositories.forEach((x) => {
                toolsheds.add(x.tool_shed);
            });
            return toolsheds.size;
        },
        fields() {
            const fields = [
                {
                    key: "name",
                    sortable: true,
                    sortByFormatted: (value, key, item) => {
                        return `${this.isLatest(item)}_${value}`;
                    },
                },
                {
                    key: "owner",
                    sortable: true,
                },
            ];
            if (this.numToolsheds > 1) {
                fields.push({
                    key: "tool_shed",
                    sortable: true,
                });
            }
            return fields;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services();
        this.load();
    },
    methods: {
        isLatest(item) {
            const value = item.tool_shed_status && item.tool_shed_status.latest_installable_revision;
            return String(value).toLowerCase() != "false";
        },
        load() {
            this.loading = true;
            this.services
                .getInstalledRepositories({ selectLatest: true })
                .then((repositories) => {
                    this.repositories = repositories;
                    this.nRepositories = repositories.length;
                    this.loading = false;
                })
                .catch((error) => {
                    this.error = error;
                });
        },
        filtered(items) {
            this.nRepositories = items.length;
        },
        toggleMonitor() {
            this.showMonitor = !this.showMonitor;
        },
        onQuery(query) {
            this.$emit("onQuery", query);
        },
    },
};
</script>
