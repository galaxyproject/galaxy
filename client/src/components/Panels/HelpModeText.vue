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
    <div class="helptext unified-panel-body d-flex justify-content-between">
        <div class="helpModeContainer" v-html="helpText"></div>
    </div>
</template>

<style>
.helptext {
    position: fixed;
    top: 70%;
    left: 80%;
    width: 20% !important;
    height: 30% !important;
    z-index: 9999;
    background-color: aliceblue;
    border-color: black;
    border-radius: 5px;
    border-width: 2px;
    border: solid;
    opacity: 90%;
}
</style>
