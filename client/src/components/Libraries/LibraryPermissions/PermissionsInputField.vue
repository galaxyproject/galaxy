<template>
    <div>
        <h2 class="h-sm">
            {{ title }}
        </h2>
        <b-row>
            <b-col>
                <div v-if="options && value" :class="permission_type">
                    <multiselect
                        v-model="value"
                        :options="fetched_options"
                        :clear-on-select="true"
                        :preserve-search="true"
                        :multiple="true"
                        label="name"
                        track-by="id"
                        :internal-search="false"
                        @input="valueChanged"
                        @search-change="searchChanged">
                        <template slot="afterList">
                            <div v-if="hasMorePages" v-observe-visibility="reachedEndOfList">
                                <span class="spinner fa fa-spinner fa-spin fa-1x" />
                            </div>
                        </template>
                    </multiselect>
                </div>
            </b-col>
            <b-col>
                <b-alert show variant="info">
                    <div v-html="alert" />
                </b-alert>
            </b-col>
        </b-row>
    </div>
</template>

<script>
import Vue from "vue";

import VueObserveVisibility from "vue-observe-visibility";
import Multiselect from "vue-multiselect";
import { Services } from "components/Libraries/LibraryPermissions/services";
import "vue-multiselect/dist/vue-multiselect.min.css";

Vue.use(VueObserveVisibility);
export default {
    components: {
        Multiselect,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
        permission_type: {
            type: String,
            required: true,
        },
        initial_value: {
            type: Array,
            required: true,
        },
        apiRootUrl: {
            type: String,
            required: true,
        },
        alert: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            permissions: undefined,
            folder: undefined,
            is_admin: undefined,
            options: undefined,
            value: undefined,
            page: 1,
            page_limit: 10,
            searchValue: "",
            fetched_options: [],
        };
    },
    computed: {
        hasMorePages() {
            return this.page * this.page_limit < this.options.total;
        },
    },
    created() {
        this.services = new Services({ root: this.root });
        // Avoid mutating a prop directly
        this.assignValue(this.initial_value);
        this.getSelectOptions();
    },
    methods: {
        getSelectOptions(searchChanged = false) {
            this.services
                .getSelectOptions(this.apiRootUrl, this.id, true, this.page, this.page_limit, this.searchValue)
                .then((response) => {
                    this.options = response;
                    if (searchChanged) {
                        this.fetched_options = this.options.roles;
                    } else {
                        this.fetched_options = this.fetched_options.concat(this.options.roles);
                    }
                });
        },
        reachedEndOfList(reached) {
            if (reached) {
                this.page++;
                this.getSelectOptions();
            }
        },
        valueChanged() {
            this.$emit("input", this.value, this.permission_type);
        },
        searchChanged(searchValue) {
            this.page = 1;
            this.searchValue = searchValue;
            this.getSelectOptions(true);
        },
        assignValue(value) {
            this.value = value;
        },
    },
};
</script>

<style scoped>
.spinner {
    text-align: center;
}
</style>
