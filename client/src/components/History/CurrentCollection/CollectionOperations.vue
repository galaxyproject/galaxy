<template>
    <nav class="d-flex justify-content-end">
        <b-button
            v-if="isRoot"
            class="mb-2 mx-3"
            title="Download Collection"
            size="sm"
            variant="link"
            :href="downloadUrl"
            download>
            <Icon icon="download" />
        </b-button>
    </nav>
</template>

<script>
export default {
    props: {
        isRoot: { type: Boolean, required: true },
        collection: { type: Object, required: true },
    },
    computed: {
        /** @return {String} */
        downloadUrl() {
            return `${this.collection.url}/download`;
        },
    },
};
</script>
