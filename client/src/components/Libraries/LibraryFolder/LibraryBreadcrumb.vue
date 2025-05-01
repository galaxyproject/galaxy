<template>
    <b-breadcrumb>
        <b-breadcrumb-item title="返回库列表" :to="{ path: `/libraries` }">
            库
        </b-breadcrumb-item>
        <template v-for="path_item in full_path">
            <b-breadcrumb-item
                :key="path_item[0]"
                :title="isCurrentId(path_item[0]) ? `您在这里` : `返回此文件夹`"
                :active="isCurrentId(path_item[0])"
                :to="{ path: `/libraries/folders/${path_item[0]}` }"
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
