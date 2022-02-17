<template>
    <section>
        <nav class="d-flex justify-content-end">
            <b-button-group>
                <IconButton
                    v-if="isRoot"
                    class="mb-2 mx-3"
                    icon="download"
                    title="Download Collection"
                    :href="downloadCollectionUrl"
                    download />
            </b-button-group>
        </nav>
    </section>
</template>

<script>
import IconButton from "components/IconButton";

export default {
    components: { IconButton },
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
