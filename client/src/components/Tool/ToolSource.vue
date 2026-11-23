<template>
    <ToolSourceProvider :id="toolId" v-slot="{ result, loading, error }" :uuid="toolUuid">
        <LoadingSpan v-if="loading" message="Waiting on tool source" />
        <GAlert v-else-if="error" variant="danger">{{ error }}</GAlert>
        <ToolSourceDisplay v-else :language="result.language" :code="result.source" />
    </ToolSourceProvider>
</template>
<script>
import { ToolSourceProvider } from "@/components/providers/ToolSourceProvider";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import ToolSourceDisplay from "@/components/Tool/ToolSourceDisplay.vue";

export default {
    components: {
        GAlert,
        LoadingSpan,
        ToolSourceProvider,
        ToolSourceDisplay,
    },
    props: {
        toolId: {
            type: String,
            required: true,
        },
        toolUuid: {
            type: String,
            default: null,
        },
    },
};
</script>
