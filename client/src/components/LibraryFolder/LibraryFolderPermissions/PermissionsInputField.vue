<template>
    <div v-if="roles.length > 0">
        <multiselect
            v-model="value"
            :options="roles"
            :clear-on-select="true"
            :preserve-search="true"
            :multiple="true"
            label="name"
            track-by="id"
            @input="valueChanged"
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
        type: {
            type: String,
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
            value: null,
            page: 1,
            page_limit: 10,
            roles: [],
        };
    },
    created() {
        this.services = new Services({ root: this.root });

        this.getSelectOptions(this.page);
    },
    computed: {
        hasMorePages() {
            return this.page * this.page_limit < this.options.total;
        },
    },
    methods: {
        getSelectOptions(page) {
            this.services.getSelectOptions(this.folder_id, true, page, this.page_limit).then((response) => {
                this.options = response;
                this.roles = this.roles.concat(this.options.roles);
            });
        },
        reachedEndOfList(reached) {
            if (reached) {
                this.getSelectOptions(this.page++);
            }
        },
        valueChanged() {
            this.$emit("input", this.value, this.type);
        },
    },
};
</script>

<style scoped>
.spinner {
    text-align: center;
}
</style>
