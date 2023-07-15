<template>
    <section>
        <nav class="content-operations d-flex justify-content-between bg-secondary">
            <GButtonGroup>
                <GButton
                    title="Download Collection"
                    class="rounded-0 text-decoration-none"
                    size="sm"
                    variant="link"
                    :href="downloadUrl"
                    @click="onDownload">
                    <Icon class="mr-1" icon="download" />
                    <span>Download</span>
                </GButton>
            </GButtonGroup>
        </nav>
    </section>
</template>

<script>
import GButton from "component-library/GButton";
import GButtonGroup from "component-library/GButtonGroup";

export default {
    components: {
        GButton,
        GButtonGroup,
    },
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
