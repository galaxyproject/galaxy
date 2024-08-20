<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useHelpModeStore } from "@/stores/helpmode/helpModeStore";
import { useUserStore } from "@/stores/userStore";

import HelpModeText from "../Help/HelpModeText.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

library.add(faExternalLinkAlt);

const { draggableActive } = storeToRefs(useHelpModeStore());
const userStore = useUserStore();

function toggleOut() {
    const panelActive = userStore.toggledSideBar === "help";
    const togglePanel = panelActive && !draggableActive.value;
    draggableActive.value = !draggableActive.value;
    if (togglePanel) {
        userStore.toggleSideBar("help");
    }
}
</script>

<template>
    <ActivityPanel title="Galaxy Help Mode">
        <template v-slot:header-buttons>
            <BButtonGroup>
                <BButton
                    v-b-tooltip.bottom.hover
                    data-description="toggle out help mode"
                    size="sm"
                    :variant="draggableActive ? 'info' : 'link'"
                    title="Toggle out help mode into a draggable window"
                    @click="toggleOut">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                </BButton>
            </BButtonGroup>
        </template>

        <template v-slot:header>
            <div v-localize class="ml-1">
                This is Galaxy's help mode. It shows help text for the current view you are interacting with.
            </div>
        </template>

        <HelpModeText class="help-text" />
    </ActivityPanel>
</template>

<style lang="scss" scoped>
.help-text {
    display: flex;
    flex-direction: column;
    overflow: auto;
}
</style>
