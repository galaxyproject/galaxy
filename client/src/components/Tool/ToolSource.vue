<template>
    <ToolSourceProvider :id="toolId" v-slot="{ result, loading, error }">
        <loading-span v-if="loading" message="Waiting on tool source" />
        <alert v-else-if="error" :message="error" variant="error" />
        <prism v-else :language="result.language" :code="result.source" :plugins="['normalize-whitespace']"></prism>
    </ToolSourceProvider>
</template>
<script>
import Alert from "components/Alert";
import LoadingSpan from "components/LoadingSpan";
import { ToolSourceProvider } from "components/providers/ToolSourceProvider";
import Prism from "vue-prismjs";
import "prismjs/themes/prism.css";
import "prismjs/plugins/normalize-whitespace/prism-normalize-whitespace.js";

export default {
    components: {
        Alert,
        LoadingSpan,
        Prism,
        ToolSourceProvider,
    },
    props: {
        toolId: {
            type: String,
            required: true,
        },
    },
};
</script>
