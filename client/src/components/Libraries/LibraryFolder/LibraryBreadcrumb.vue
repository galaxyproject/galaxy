<template>
    <BBreadcrumb>
        <BBreadcrumbItem title="Return to the list of libraries" :to="{ path: `/libraries` }">
            Libraries
        </BBreadcrumbItem>
        <template v-for="path_item in full_path" :key="path_item[0]">
            <BBreadcrumbItem
                :title="isCurrentId(path_item[0]) ? `You are here` : `Return to this folder`"
                :active="isCurrentId(path_item[0])"
                :to="{ path: `/libraries/folders/${path_item[0]}` }"
                href="#"
                >{{ path_item[1] }}</BBreadcrumbItem
            >
        </template>
    </BBreadcrumb>
</template>
<script>
import { BBreadcrumb, BBreadcrumbItem } from "bootstrap-vue";

export default {
    components: { BBreadcrumb, BBreadcrumbItem },
    props: {
        full_path: {
            type: Array,
            required: true,
        },
        currentId: {
            type: String,
            required: false,
            default: undefined,
        },
    },
    methods: {
        isCurrentId(id) {
            return this.currentId === id;
        },
    },
};
</script>
