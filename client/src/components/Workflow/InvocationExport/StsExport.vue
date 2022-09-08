<template>
    <StsDownloadButton :downloadEndpoint="invocationDownloadUrl" title="Download Invocation"> </StsDownloadButton>
</template>

<script>
import StsDownloadButton from "components/Markdown/StsDownloadButton";

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
