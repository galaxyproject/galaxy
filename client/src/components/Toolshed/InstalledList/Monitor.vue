<template>
    <div>
        <b-alert v-if="error" variant="danger" show>
            {{ error }}
        </b-alert>
        <b-card v-if="showItems" no-body class="my-2">
            <h2 class="m-3 h-text">正在安装中...</h2>
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
                    <b>状态: </b><span>{{ row.item.status }}</span>
                </template>
                <template v-slot:cell(actions)="row">
                    <InstallationActions
                        class="float-right"
                        :status="row.item.status"
                        @onUninstall="uninstallRepository(row.item)" />
                </template>
            </b-table>
        </b-card>
        <b-alert v-if="showEmpty" variant="info" show> 目前没有正在安装的仓库。 </b-alert>
    </div>
</template>
<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import InstallationActions from "../RepositoryDetails/InstallationActions";
import { Services } from "../services";

Vue.use(BootstrapVue);

export default {
    components: {
        InstallationActions,
    },
    data() {
        return {
            delay: 5000,
            loading: true,
            error: null,
            items: [],
            fields: ["名称", "状态", "操作"],
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
