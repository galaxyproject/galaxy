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
            <!-- for each item in useHelpModeTextStore, display them -->
            <!-- <div v-for="item in helpText" :key="item.id" class="helpModeText">
                <a class="helpModeText-link" :href="item.href">{{ item }}</a>
            </div> -->
            HELP TEXT DISPLAYED HERE <br />
            {{ helpText }}
        </div>
    </div>
</template>
