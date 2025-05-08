<template>
    <ToolSourceProvider :id="toolId" v-slot="{ result, loading, error }">
        <LoadingSpan v-if="loading" message="Waiting on tool source" />
        <Alert v-else-if="error" :message="error" variant="error" />
        <ToolSourceDisplay v-else :language="result.language" :code="result.source" />
    </ToolSourceProvider>
</template>
<script>
import Alert from "components/Alert";
import LoadingSpan from "components/LoadingSpan";
import { ToolSourceProvider } from "components/providers/ToolSourceProvider";

import ToolSourceDisplay from "@/components/Tool/ToolSourceDisplay.vue";

export default {
    components: {
        Alert,
        LoadingSpan,
        ToolSourceProvider,
        ToolSourceDisplay,
    },
    props: {
        toolId: {
            type: String,
            required: true,
        },
    },
};
</script>
