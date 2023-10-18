<script setup="ts">
import MarkdownIt from "markdown-it";
import { computed } from "vue";

import { useHelpModeTextStore } from "@/stores/helpmode/helpModeTextStore";

const md = MarkdownIt();
const helpInfo = useHelpModeTextStore();

const helpText = computed({
    get() {
        return md.render(helpInfo.helpmodetext);
    },
});
</script>

<template>
    <div class="unified-panel-body d-flex justify-content-between">
        <div class="helpModeContainer" v-html="helpText"></div>
    </div>
</template>
