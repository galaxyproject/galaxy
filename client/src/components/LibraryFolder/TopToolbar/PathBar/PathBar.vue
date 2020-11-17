<template>
    <b-breadcrumb>
        <b-breadcrumb-item title="Return to the list of libraries" :href="libRootPath">
            Libraries
        </b-breadcrumb-item>
        <template v-for="path_item in full_path">
            <b-breadcrumb-item :active="id == path_item[0]" :href="path_item[0]">{{ path_item[1] }}</b-breadcrumb-item>
        </template>
    </b-breadcrumb>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

export default {
    name: "PathBar",
    props: {
        full_path: {
            type: Array,
            required: true,
        },
        id: {
            type: String,
            required: true,
        },
        parent_library_id: {
            type: String,
            required: true,
        },
    },
    computed: {
        libRootPath() {
            return `${getAppRoot()}library/list`;
        },
        upper_folder_id() {
            if (this.full_path.length === 1) {
                // the library is above us
                return 0;
            } else {
                return this.full_path[this.full_path.length - 2][0];
            }
        },
    },
};
</script>
