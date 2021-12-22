<template>
    <b-breadcrumb>
        <b-breadcrumb-item title="Return to the list of libraries" :to="{ path: `/` }"> Libraries </b-breadcrumb-item>
        <template v-for="path_item in full_path">
            <b-breadcrumb-item
                :key="path_item[0]"
                :title="isCurrentId(path_item[0]) ? `You are here` : `Return to this folder`"
                :active="isCurrentId(path_item[0])"
                :to="{ path: `/folders/${path_item[0]}` }"
                href="#"
                >{{ path_item[1] }}</b-breadcrumb-item
            >
        </template>
    </b-breadcrumb>
</template>
<script>
export default {
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
