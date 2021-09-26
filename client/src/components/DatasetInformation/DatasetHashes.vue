<template>
    <span class="dataset-hashes">
        <ul class="dataset-hashes-list">
            <DatasetHash v-for="(hash, index) in hashes" :key="index" :hash="hash" />
        </ul>
    </span>
</template>

<script>
import DatasetHash from "./DatasetHash";

export default {
    components: {
        DatasetHash,
    },
    props: {
        hashes: {
            type: Array,
            required: true,
        },
    },
};
</script>

<style scoped>
.dataset-hashes-list {
    padding-inline-start: 20px;
    margin-bottom: 0px;
}
</style>
