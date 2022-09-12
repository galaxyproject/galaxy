<template>
    <StsDownloadButton :download-endpoint="invocationDownloadUrl" title="Download Invocation" />
</template>

<script>
import StsDownloadButton from "components/StsDownloadButton";

export default {
    components: {
        StsDownloadButton,
    },
    props: {
        invocationId: {
            type: String,
            required: true,
        },
    },
    computed: {
        invocationDownloadUrl() {
            return `/api/invocations/${this.invocationId}/prepare_store_download`;
        },
    },
};
</script>
