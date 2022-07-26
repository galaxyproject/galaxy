<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <b-button-group>
                <b-button
                    title="Download Collection"
                    class="rounded-0 text-decoration-none"
                    size="sm"
                    variant="link"
                    @click="onDownload">
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
    methods: {
        onDownload() {
            window.location.href = this.downloadUrl;
        },
    },
};
</script>
