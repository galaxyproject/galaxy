<template>
    <div v-if="options && value">
        <multiselect
            v-model="value"
            :options="fetched_options"
            :clear-on-select="true"
            :preserve-search="true"
            :multiple="true"
            label="name"
            track-by="id"
            @input="valueChanged"
            @search-change="searchChanged"
            :internal-search="false"
        >
            <template slot="afterList">
                <div v-observe-visibility="reachedEndOfList" v-if="hasMorePages">
                    <span class="spinner fa fa-spinner fa-spin fa-1x" />
                </div>
            </template>
        </multiselect>
    </div>
</template>

<script>
import Multiselect from "vue-multiselect";
import { Services } from "./services";

export default {
    props: {
        folder_id: {
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
    },
    components: {
        Multiselect,
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
    created() {
        this.services = new Services({ root: this.root });
        // Avoid mutating a prop directly
        this.value = this.initial_value;
        this.getSelectOptions();
    },
    computed: {
        hasMorePages() {
            return this.page * this.page_limit < this.options.total;
        },
    },
    methods: {
        getSelectOptions(searchChanged = false) {
            this.services
                .getSelectOptions(this.folder_id, true, this.page, this.page_limit, this.searchValue)
                .then((response) => {
                    this.options = response;
                    if (searchChanged) this.fetched_options = this.options.roles;
                    else this.fetched_options = this.fetched_options.concat(this.options.roles);
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
    },
};
</script>

<style scoped>
.spinner {
    text-align: center;
}
</style>
