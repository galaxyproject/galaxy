<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTimes, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDraggable } from "@vueuse/core";
import { BButton } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { reactive, ref, watch } from "vue";

import { useAnimationFrameSize } from "@/composables/sensors/animationFrameSize";
import { useHelpModeStore } from "@/stores/helpmode/helpModeStore";
import { useUserStore } from "@/stores/userStore";

import HelpModeText from "./HelpModeText.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faTimes, faUndo);

const userStore = useUserStore();

// local refs
const { draggableActive, position, helpModeStyle } = storeToRefs(useHelpModeStore());
const el = ref<HTMLElement | null>(null);
const helpModeHeader = ref<HTMLElement | null>(null);
const helpModeSize = reactive(useAnimationFrameSize(el));

// draggable properties
const { style } = useDraggable(helpModeHeader, { initialValue: position.value });

// update store position on drag
watch(
    () => style.value,
    (newStyle) => {
        if (newStyle) {
            // TODO: This might be a little hacky?...
            // convert str of form "left:{...}px;top:{...}px;" to
            // extract left and top and place in helpModeStyle
            const [left, top] = newStyle.split(";");
            let leftVal = left?.split(":")[1];
            let topVal = top?.split(":")[1];
            if (parseInt(leftVal || "") < 0) {
                leftVal = "0";
            }
            if (parseInt(topVal || "") < 0) {
                topVal = "0";
            }
            helpModeStyle.value = {
                ...helpModeStyle.value,
                left: leftVal,
                top: topVal,
            };
        }
    }
);

// update store dimensions on resize
watch(
    () => [helpModeSize.width, helpModeSize.height],
    ([newWidth, newHeight]) => {
        if (newWidth && newHeight) {
            helpModeStyle.value = {
                ...helpModeStyle.value,
                width: `${newWidth}px`,
                height: `${newHeight}px`,
            };
        }
    }
);

/** Close the draggable help mode and toggle the sidebar */
function closeDraggable() {
    const panelActive = userStore.toggledSideBar !== "";
    draggableActive.value = false;
    if (!panelActive) {
        userStore.toggleSideBar("help");
    }
}

/** Reset the position of the help mode to default */
function resetPosition() {
    helpModeStyle.value = {
        width: "25%",
        height: "30%",
        left: "0",
        top: "0",
    };
}
</script>

<template>
    <div ref="el" :style="[style, helpModeStyle]" class="help-text justify-content-between">
        <div ref="helpModeHeader" class="header unselectable">
            <Heading h4 inline size="sm" class="flex-grow-1 mx-2">Galaxy Help Mode</Heading>
            <BButton size="sm" @click="resetPosition">
                <FontAwesomeIcon :icon="faUndo" />
            </BButton>
            <BButton size="sm" @click="closeDraggable">
                <FontAwesomeIcon :icon="faTimes" />
            </BButton>
        </div>
        <HelpModeText tabbed />
    </div>
</template>

<style scoped lang="scss">
// TODO: Maybe use predefined variables for colors and sizes?
.help-text {
    display: flex;
    flex-direction: column;
    z-index: 9999;
    background-color: aliceblue;
    border-color: black;
    border-radius: 5px;
    border-width: 2px;
    border: solid;
    opacity: 90%;
    position: fixed;
    resize: both;
    overflow: auto;
}
.header {
    display: flex;
    color: white;
    background-color: #454d6b;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #868686;
    cursor: move;
}
</style>
