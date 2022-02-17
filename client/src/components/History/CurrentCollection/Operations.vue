<template>
    <section>
        <nav class="d-flex justify-content-end">
            <b-button-group>
                <b-button
                    v-if="isRoot"
                    class="mb-2 mx-3"
                    title="Download Collection"
                    :href="downloadCollectionUrl"
                    download>
                    <Icon icon="download" />
                </b-button>
            </b-button-group>
        </nav>
    </section>
</template>

<script>
export default {
    props: {
        isRoot: { type: Boolean, required: true },
        collection: { type: Object, required: true },
    },
    computed: {
        /** @return {String} */
        downloadCollectionUrl() {
            return `${this.collection.url}/download`;
        },
    },
};
</script>
