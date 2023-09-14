<script setup="ts">
import { computed } from "vue";

import { useHelpModeTextStore } from "@/stores/helpmode/helpModeTextStore";

const helpInfo = useHelpModeTextStore();

const helpText = computed({
    get() {
        return helpInfo.helpmodetext;
    },
});
</script>

<template>
    <div class="unified-panel-body d-flex justify-content-between">
        <div class="helpModeContainer">
            {{ helpText }}
        </div>
    </div>
</template>
