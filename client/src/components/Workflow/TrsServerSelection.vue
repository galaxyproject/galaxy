<!-- Modelled after Sam's ToolShed ServerSelection.vue -->
<template>
    <span v-if="!loading" class="m-1 text-muted">
        <span v-if="showDropdown" class="dropdown">
            <b-link
                id="dropdownTrsServer"
                data-toggle="dropdown"
                aria-haspopup="true"
                aria-expanded="false"
                class="font-weight-bold"
            >
                {{ selection.label }}
                <span class="fa fa-caret-down" />
            </b-link>
            <div class="dropdown-menu" aria-labelledby="dropdownTrsServer">
                <a
                    v-for="selection in trsServers"
                    :key="selection.id"
                    class="dropdown-item"
                    href="javascript:void(0)"
                    role="button"
                    @click.prevent="onUrlSelection(selection)"
                    >{{ selection.label }}</a
                >
            </div>
        </span>
        <span v-else>
            <b-link :href="selection.link_url" target="_blank" class="font-weight-bold" :title="selection.doc">
                {{ selection.label }}
            </b-link>
        </span>
    </span>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        selection: {
            type: Object,
        },
        trsServers: {
            type: Array,
        },
        loading: {
            type: Boolean,
        },
    },
    computed: {
        showDropdown() {
            return this.trsServers.length > 1;
        },
    },
    methods: {
        onTrsSelection(selection) {
            this.$emit("onTrsSelection", selection);
        },
    },
};
</script>
<style scoped>
span.dropdown {
    display: inline-block;
}
</style>
