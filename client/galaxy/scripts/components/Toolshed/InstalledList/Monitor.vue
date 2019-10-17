<template>
    <div class="installation-monitor">
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <loading-span v-if="loading" message="Loading currently installing repositories" />
            <div v-else>
                <b-table sticky-header thead-class="installation-monitor-header" :items="items" :fields="fields">
                    <template v-slot:cell(name)="data">
                        <b-link @click="onQuery(data.value)">
                            {{ data.value }}
                        </b-link>
                    </template>
                    <template v-slot:cell(status)="data">
                        <b-button class="btn-sm text-nowrap" disabled variant="info">
                            {{ data.value }}
                        </b-button>
                    </template>
                </b-table>
                <div v-if="showEmpty" class="text-center">
                    Currently no repositories are being installed.
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "../services.js";
import LoadingSpan from "components/LoadingSpan";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan
    },
    data() {
        return {
            loading: true,
            error: null,
            items: [],
            fields: ["name", "owner", "status"]
        };
    },
    computed: {
        showEmpty() {
            return this.items.length === 0;
        }
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.load();
    },
    methods: {
        load() {
            this.loading = true;
            this.services
                .getInstalledRepositories({
                    filter: x => x.status !== "Installed"
                })
                .then(items => {
                    this.items = items;
                    this.loading = false;
                })
                .catch(error => {
                    this.error = error;
                });
        },
        onQuery(q) {
            this.$emit("onQuery", q);
        }
    }
};
</script>
<style>
.installation-monitor {
    height: 300px;
    min-width: 500px;
}
.installation-monitor-header {
    display: none;
}
</style>
