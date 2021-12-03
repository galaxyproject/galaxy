<template>
    <span class="dataset-sources">
        <ul class="dataset-sources-list">
            <DatasetSource v-for="(source, index) in sources" :key="index" :source="source" />
        </ul>
    </span>
</template>

<script>
import DatasetSource from "./DatasetSource";

export default {
    components: {
        DatasetSource,
    },
    props: {
        sources: {
            type: Array,
            required: true,
        },
    },
};
</script>

<style scoped>
.dataset-sources-list {
    padding-inline-start: 20px;
    margin-bottom: 0px;
}
</style>
