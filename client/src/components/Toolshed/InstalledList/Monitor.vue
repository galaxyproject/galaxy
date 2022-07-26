<template>
    <div>
        <b-alert v-if="error" variant="danger" show>
            {{ error }}
        </b-alert>
        <b-card v-if="showItems" no-body class="my-2">
            <h5 class="m-3">Currently installing...</h5>
            <b-table
                class="mx-3 mb-0"
                sticky-header
                thead-class="installation-monitor-header"
                :items="items"
                :fields="fields">
                <template v-slot:cell(name)="row">
                    <b-link @click="onQuery(row.item.name)"> {{ row.item.name }} ({{ row.item.owner }}) </b-link>
                </template>
                <template v-slot:cell(status)="row">
                    <InstallationButton
                        class="float-right"
                        :status="row.item.status"
                        @onUninstall="uninstallRepository(row.item)" />
                </template>
            </b-table>
        </b-card>
        <b-alert v-if="showEmpty" variant="info" show> Currently there are no installing repositories. </b-alert>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { Services } from "../services";
import InstallationButton from "../RepositoryDetails/InstallationButton";

Vue.use(BootstrapVue);

export default {
    components: {
        InstallationButton,
    },
    data() {
        return {
            delay: 5000,
            loading: true,
            error: null,
            items: [],
            fields: ["name", "status"],
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
<style>
.installation-monitor-header {
    display: none;
}
</style>
