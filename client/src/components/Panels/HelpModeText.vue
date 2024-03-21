<script setup lang="ts">
import { useDraggable } from "@vueuse/core";
import MarkdownIt from "markdown-it";
import { computed, onMounted, ref } from "vue";

import { useHelpModeStatusStore } from "@/stores/helpmode/helpModeStatusStore";
import { useHelpModeTextStore } from "@/stores/helpmode/helpModeTextStore";

const md = MarkdownIt();
const helpInfo = useHelpModeTextStore();
const status = useHelpModeStatusStore();
const helpText = computed({
    get() {
        return md.render(helpInfo.helpmodetext);
    },
    set() {
        //do nothing, this is set in components that add helptext
    },
});
const helpStatus = computed({
    get() {
        return status.helpmodestatus;
    },
    set(value: boolean) {
        status.setHelpModeStatus(value);
    },
});
function closeHelpMode() {
    helpStatus.value = !helpStatus.value;
}
const el = ref<HTMLElement | null>(null);
const { x, y, style } = useDraggable(el, {
    initialValue: { x: 0, y: 0 },
});
const helpTextRef = ref(null);
onMounted(() => {
    const links = (helpTextRef.value as unknown as HTMLElement).querySelectorAll("a");
    links.forEach((link: HTMLAnchorElement) => {
        link.setAttribute("target", "_blank");
    });
});
</script>
<template>
    <div
        ref="el"
        :style="style"
        style="position: fixed"
        class="helptext unified-panel-body d-flex justify-content-between">
        <div class="header">
            <h1>Galaxy Help Mode</h1>
            <button class="close-button" @click="closeHelpMode">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div ref="helpTextRef" class="help-mode-container" v-html="helpText"></div>
    </div>
</template>
<style>
.helptext {
    display: flex;
    flex-direction: column;
    width: 25% !important;
    height: 30% !important;
    z-index: 9999;
    background-color: aliceblue;
    border-color: black;
    border-radius: 5px;
    border-width: 2px;
    border: solid;
    opacity: 90%;
}
.header {
    display: flex;
    color: white;
    background-color: #454d6b;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #868686;
    /* padding-bottom: 10px; */
}
.help-mode-container {
    margin-top: 0;
    padding: 10px;
    overflow-y: auto;
    height: 100%;
}
</style>
