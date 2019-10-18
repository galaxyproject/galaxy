<template>
    <b-card v-if="showItems" title="Currently installing..." title-tag="h5">
        <b-table sticky-header thead-class="installation-monitor-header" :items="items" :fields="fields">
            <template v-slot:cell(name)="data">
                <b-link @click="onQuery(data.value)">
                    {{ data.value }}
                </b-link>
            </template>
            <template v-slot:cell(status)="data">
                <b-button class="btn-sm text-nowrap float-right" disabled variant="info">
                    <span class="fa fa-spinner fa-spin mr-1"/>
                    <span>{{ data.value }}</span>
                </b-button>
            </template>
        </b-table>
    </b-card>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
import LoadingSpan from "components/LoadingSpan";

Vue.use(BootstrapVue);

export default {
    components: {
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
        }
    }
};
</script>
<style>
.installation-monitor-header {
    display: none;
}
</style>
