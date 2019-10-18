<template>
    <div>
        <b-alert v-if="error" variant="danger" show>
            {{ error }}
        </b-alert>
        <b-card v-if="showItems" title="Currently installing..." title-tag="h5">
            <b-table sticky-header thead-class="installation-monitor-header" :items="items" :fields="fields">
                <template v-slot:cell(name)="data">
                    <b-link @click="onQuery(data.value)">
                        {{ data.value }}
                    </b-link>
                </template>
                <template v-slot:cell(status)="row">
                    <InstallationButton
                        class="float-right"
                        :status="row.item.status"
                        @onUninstall="uninstallRepository(row.item)"
                    />
                </template>
            </b-table>
        </b-card>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import InstallationButton from "./RepositoryDetails/InstallationButton.vue";
import LoadingSpan from "components/LoadingSpan";

Vue.use(BootstrapVue);

export default {
    components: {
        InstallationButton,
        LoadingSpan
    },
    data() {
        return {
            delay: 1000,
            loading: true,
            error: null,
            items: [],
            fields: ["name", "owner", "status"]
        };
    },
    computed: {
        showItems() {
            return this.items.length > 0;
        }
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    destroyed() {
        clearTimeout(this.timeout);
    },
    methods: {
        setTimeout() {
            this.timeout = setTimeout(() => {
                this.load();
            }, this.delay);
        },
        load() {
            this.loading = true;
            this.services
                .getInstalledRepositories({
                    filter: x => x.status !== "Installed"
                })
                .then(items => {
                    this.items = items;
                    this.loading = false;
                    this.setTimeout();
                })
                .catch(error => {
                    this.error = error;
                });
        },
        onQuery(q) {
            this.$emit("onQuery", q);
        },
        uninstallRepository: function(repo) {
            this.services
                .uninstallRepository(repo)
                .catch(error => {
                    this.error = error;
                });
        }
    }
};
</script>
<style>
.installation-monitor-header {
    display: none;
}
</style>
