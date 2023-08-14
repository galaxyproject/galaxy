<template>
    <span>
        {{ title }}
        <div v-for="(grant, index) in funding" :key="index">
            <GrantViewer :grant="grant" />
        </div>
    </span>
</template>

<script>
import GrantViewer from "./GrantViewer";

export default {
    components: {
        GrantViewer,
    },
    props: {
        title: {
            type: String,
            default: "",
        },
        funding: {
            type: Array,
        },
    },
};
</script>
