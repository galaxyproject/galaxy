<template>
    <div>
        <b-alert v-if="error" variant="danger" show>
            {{ error }}
        </b-alert>

        <GCard v-if="showItems" class="my-2">
            <h2 class="m-3 h-text">Currently installing...</h2>

            <GTable :items="items" :fields="fields" hide-header class="m-2">
                <template v-slot:cell(name)="row">
                    <b-link @click="onQuery(row.item.name)"> {{ row.item.name }} ({{ row.item.owner }}) </b-link>
                </template>
                <template v-slot:cell(status)="row">
                    <b>Status: </b><span>{{ row.item.status }}</span>
                </template>
                <template v-slot:cell(actions)="row">
                    <InstallationActions
                        class="float-right"
                        :status="row.item.status"
                        @onUninstall="uninstallRepository(row.item)" />
                </template>
            </GTable>
        </GCard>

        <b-alert v-if="showEmpty" variant="info" show> Currently there are no installing repositories. </b-alert>
    </div>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { Services } from "../services";

import InstallationActions from "../RepositoryDetails/InstallationActions.vue";
import GCard from "@/components/Common/GCard.vue";
import GTable from "@/components/Common/GTable.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        GCard,
        GTable,
        InstallationActions,
    },
    data() {
        return {
            delay: 5000,
            loading: true,
            error: null,
            items: [],
            fields: [
                {
                    key: "name",
                    label: "Name",
                },
                {
                    key: "status",
                    label: "Status",
                },
                {
                    key: "actions",
                    label: "Actions",
                },
            ],
        };
    },
    computed: {
        showItems() {
            return this.items.length > 0;
        },
        showEmpty() {
            return !this.loading && this.items.length === 0;
        },
    },
    created() {
        this.services = new Services();
        this.load();
    },
    destroyed() {
        this.clearTimeout();
    },
    methods: {
        setTimeout() {
            this.clearTimeout();
            this.timeout = setTimeout(() => {
                this.load();
            }, this.delay);
        },
        clearTimeout() {
            if (this.timeout) {
                clearTimeout(this.timeout);
            }
        },
        load() {
            this.services
                .getInstalledRepositories({
                    filter: (x) => x.status !== "Installed",
                })
                .then((items) => {
                    this.items = items;
                    this.loading = false;
                    this.setTimeout();
                })
                .catch((error) => {
                    this.error = error;
                });
        },
        onQuery(q) {
            this.$emit("onQuery", q);
        },
        uninstallRepository: function (repository) {
            this.services.uninstallRepository(repository).catch((error) => {
                this.error = error;
            });
        },
    },
};
</script>
