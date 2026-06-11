<script setup lang="ts">
import { faAngleDoubleDown, faColumns, faExpand } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { useChatStore } from "@/stores/chatStore.js";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";

const route = useRoute();
const router = useRouter();

const chatStore = useChatStore();

const { activeChatId, isBottomPanelOpen, isCenterMode, isRightPanelOpen } = storeToRefs(chatStore);

const isOnGalaxyAIRoute = computed(() => route.path.startsWith("/galaxyai"));

const isOnCenter = computed(() => isCenterMode.value && isOnGalaxyAIRoute.value);

function openCenterChat() {
    const chatId = activeChatId.value;
    chatStore.setLocation("center");
    chatStore.hideChat();
    router.push(chatId ? `/galaxyai/${chatId}` : "/galaxyai");
}

function openDockedChat(location: "right" | "bottom") {
    /** Stores an id if there is a `/galaxyai/:exchangeId` route param */
    const routedChatId = route.path.includes("galaxyai") ? route.params["exchangeId"] || null : null;
    const wasCenterMode = chatStore.isCenterMode;

    if (isOnGalaxyAIRoute.value) {
        router.push("/");
    }

    // TODO: What if we just looked at a chat, maybe add a chatId to localStorage for last opened chat?
    const chatId = wasCenterMode && routedChatId ? routedChatId : chatStore.resolveDockChatId();
    chatStore.dockChat(location, chatId);
}
</script>

<template>
    <GButtonGroup class="chat-mode-selector" size="small">
        <GButton color="blue" outline :pressed="isOnCenter" title="Enable Full View" tooltip @click="openCenterChat">
            <FontAwesomeIcon :icon="faExpand" />
        </GButton>
        <GButton
            color="blue"
            outline
            :pressed="isRightPanelOpen"
            title="Dock To Side Panel"
            tooltip
            @click="openDockedChat('right')">
            <FontAwesomeIcon :icon="faColumns" />
        </GButton>
        <GButton
            color="blue"
            outline
            :pressed="isBottomPanelOpen"
            title="Dock To Bottom Panel"
            tooltip
            @click="openDockedChat('bottom')">
            <FontAwesomeIcon :icon="faAngleDoubleDown" />
        </GButton>
    </GButtonGroup>
</template>

<style scoped lang="scss">
.chat-mode-selector {
    width: 100%;
    display: flex;
    justify-content: space-between;

    .g-button {
        width: 100%;
        justify-content: center;
    }
}
</style>
