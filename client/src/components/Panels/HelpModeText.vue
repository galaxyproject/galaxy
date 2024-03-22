<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDraggable } from "@vueuse/core";
import { BButton } from "bootstrap-vue";
import MarkdownIt from "markdown-it";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { useHelpModeStatusStore } from "@/stores/helpmode/helpModeStatusStore";
import { useHelpModeTextStore } from "@/stores/helpmode/helpModeTextStore";

import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

library.add(faTimes);

const md = MarkdownIt();

// local refs
const { content, loading } = storeToRefs(useHelpModeTextStore());
const { status, position } = storeToRefs(useHelpModeStatusStore());
const el = ref<HTMLElement | null>(null);
const helpModeHeader = ref<HTMLElement | null>(null);
const helpTextRef = ref(null);

// local computed refs
const helpText = computed({
    get() {
        return md.render(content.value);
    },
    set() {
        //do nothing, this is set in components that add helptext
    },
});

// draggable properties
const {
    x: dragX,
    y: dragY,
    style,
} = useDraggable(helpModeHeader, {
    initialValue: position.value,
});
// watch both x and y, and do something if they change:
watch(
    () => [dragX.value, dragY.value],
    ([newX, newY]) => {
        if (newX && newY) {
            position.value = { x: newX, y: newY };
        }
    }
);

onMounted(() => {
    const links = (helpTextRef.value as unknown as HTMLElement).querySelectorAll("a");
    links.forEach((link: HTMLAnchorElement) => {
        link.setAttribute("target", "_blank");
    });
});
</script>

<template>
    <div ref="el" :style="style" class="help-text unified-panel-body d-flex justify-content-between">
        <div ref="helpModeHeader" class="header">
            <Heading h4 inline size="sm" class="flex-grow-1 mx-2">Galaxy Help Mode</Heading>
            <BButton class="close-button" size="sm" @click="status = false">
                <FontAwesomeIcon :icon="faTimes" />
            </BButton>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-if="!loading" ref="helpTextRef" class="help-mode-container" v-html="helpText" />
        <LoadingSpan v-else message="Loading help text" />
    </div>
</template>

<style scoped lang="scss">
.help-text {
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
    position: fixed;
}
.header {
    display: flex;
    color: white;
    background-color: #454d6b;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #868686;
    cursor: move;
    /* padding-bottom: 10px; */
}
.help-mode-container {
    margin-top: 0;
    padding: 10px;
    overflow-y: auto;
    height: 100%;
}
</style>
