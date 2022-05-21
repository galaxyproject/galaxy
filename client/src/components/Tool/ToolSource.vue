<template>
    <ToolSourceProvider :id="toolId" v-slot="{ result, loading, error }">
        <loading-span v-if="loading" message="Waiting on tool source" />
        <alert v-else-if="error" :message="error" variant="error" />
        <tool-source-display v-else :language="result.language" :code="result.source" />
    </ToolSourceProvider>
</template>
<script>
import Alert from "components/Alert";
import LoadingSpan from "components/LoadingSpan";
import { ToolSourceProvider } from "components/providers/ToolSourceProvider";

export default {
    components: {
        Alert,
        LoadingSpan,
        ToolSourceProvider,
        ToolSourceDisplay: () => import(/* webpackChunkName: "ToolSourceDisplay" */ "./ToolSourceDisplay.vue"),
    },
    props: {
        toolId: {
            type: String,
            required: true,
        },
    },
};
</script>
