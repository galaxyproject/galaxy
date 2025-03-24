<template>
    <ToolSourceProvider :id="toolId" v-slot="{ result, loading, error }">
        <LoadingSpan v-if="loading" message="正在获取工具源码" />
        <Alert v-else-if="error" :message="error" variant="error" />
        <ToolSourceDisplay v-else :language="result.language" :code="result.source" />
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
