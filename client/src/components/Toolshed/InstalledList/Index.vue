<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <LoadingSpan v-if="loading" message="Loading installed repositories" />
            <div v-else>
                <BAlert :variant="messageVariant" :show="showMessage">{{ message }}</BAlert>

                <div class="m-1">
                    <span class="installed-message text-muted">
                        {{ repositories.length }} repositories installed on this instance.
                    </span>

                    <GLink class="font-weight-bold" @click="toggleMonitor">
                        <span v-if="showMonitor">
                            <FontAwesomeIcon :icon="faAngleDoubleUp" />
                            <span>Hide installation progress.</span>
                        </span>
                        <span v-else>
                            <FontAwesomeIcon :icon="faAngleDoubleDown" />
                            <span>Show installation progress.</span>
                        </span>
                    </GLink>
                </div>

                <Monitor v-if="showMonitor" @onQuery="onQuery" />

                <GTable
                    id="repository-table"
                    :fields="fields"
                    :items="repositories"
                    :filter="filter"
                    @filtered="filtered">
                    <template v-slot:cell(name)="{ item, toggleDetails }">
                        <GLink class="font-weight-bold" @click.prevent="toggleDetails">
                            <div v-if="!isLatest(item)">
                                <BBadge variant="danger" class="mb-2"> Newer version available! </BBadge>
                            </div>

                            <div class="name">{{ item.name }}</div>
                        </GLink>

                        <div>{{ item.description }}</div>
                    </template>

                    <template v-slot:row-details="{ item }">
                        <RepositoryDetails :repo="item" />
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
import { faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge } from "bootstrap-vue";

import { getAppRoot } from "@/onload/loadConfig";

import { Services } from "../services";

import RepositoryDetails from "./Details.vue";
import Monitor from "./Monitor.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GTable from "@/components/Common/GTable.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

export default {
    components: {
        BAlert,
        BBadge,
        FontAwesomeIcon,
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
            faAngleDoubleDown,
            faAngleDoubleUp,
            error: null,
            loading: true,
            message: null,
            messageVariant: null,
            nRepositories: 0,
            repositories: [],
            showMonitor: false,
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
                    label: "Name",
                    sortable: true,
                },
                {
                    key: "owner",
                    label: "Owner",
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
