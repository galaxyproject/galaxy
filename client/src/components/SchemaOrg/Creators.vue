<template>
    <span>
        {{ title }}
        <div v-for="(creator, index) in creators" :key="index">
            <CreatorViewer :creator="creator" />
        </div>
    </span>
</template>

<script>
import CreatorViewer from "./CreatorViewer";

export default {
    components: {
        CreatorViewer,
    },
    props: {
        title: {
            type: String,
            default: "",
        },
        creators: {
            type: Array,
        },
    },
};
</script>
