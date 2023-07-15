<template>
    <GBreadcrumb>
        <GBreadcrumbItem title="Return to the list of libraries" :to="{ path: `/libraries` }">
            Libraries
        </GBreadcrumbItem>
        <template v-for="path_item in full_path">
            <GBreadcrumbItem
                :key="path_item[0]"
                :title="isCurrentId(path_item[0]) ? `You are here` : `Return to this folder`"
                :active="isCurrentId(path_item[0])"
                :to="{ path: `/libraries/folders/${path_item[0]}` }"
                href="#">
                {{ path_item[1] }}
            </GBreadcrumbItem>
        </template>
    </GBreadcrumb>
</template>

<script>
import GBreadcrumb from "@/component-library/GBreadcrumb.vue";
import GBreadcrumbItem from "@/component-library/GBreadcrumbItem.vue";

export default {
    components: {
        GBreadcrumb,
        GBreadcrumbItem,
    },
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
