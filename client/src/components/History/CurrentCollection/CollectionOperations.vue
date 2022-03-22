<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <b-button-group>
                <b-button title="Download Collection" size="sm" variant="link" download :href="downloadUrl">
                    <Icon class="mr-1" icon="download" />
                    <span>Download</span>
                </b-button>
            </b-button-group>
        </nav>
    </section>
</template>

<script>
export default {
    props: {
        dsc: { type: Object, required: true },
    },
    computed: {
        /** @return {String} */
        downloadUrl() {
            return `${this.dsc.url}/download`;
        },
    },
};
</script>
