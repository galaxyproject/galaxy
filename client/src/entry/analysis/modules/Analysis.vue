<script setup>
import { faChevronLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { usePanels } from "@/composables/usePanels";
import { useChatStore } from "@/stores/chatStore";
import { useUserStore } from "@/stores/userStore";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import ChatGXY from "@/components/ChatGXY.vue";
import ChatPanel from "@/components/ChatGXY/ChatPanel.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const chatStore = useChatStore();
const { isRightPanelOpen, isBottomPanelOpen, activeChatId } = storeToRefs(chatStore);
const { historyPanelWidth, chatPanelWidth } = storeToRefs(useUserStore());

const route = useRoute();
const router = useRouter();

watch(
    () => route.path,
    (newPath) => {
        if (newPath.startsWith("/chatgxy")) {
            chatStore.hideChat();
        }
    },
);

const showCenter = ref(false);
const { showPanels } = usePanels();

const historyPanel = ref(null);

// methods
function hideCenter() {
    showCenter.value = false;
}

function onShow(showPanel) {
    if (historyPanel.value) {
        historyPanel.value.show = showPanel;
    }
}

function onLoad() {
    showCenter.value = true;
}

function handleUndock() {
    const chatId = activeChatId.value;
    chatStore.setLocation("center");
    chatStore.hideChat();
    router.push(chatId ? `/chatgxy/${chatId}` : "/chatgxy");
}

// life cycle
onMounted(() => {
    // Using a custom event here which, in contrast to watching $route,
    // always fires when a route is pushed instead of validating it first.
    router.app.$on("router-push", hideCenter);
});

onUnmounted(() => {
    router.app.$off("router-push", hideCenter);
});
</script>

<template>
    <div id="columns" class="d-flex">
        <ActivityBar v-if="showPanels" />
        <div id="center" class="d-flex flex-column w-100">
            <div class="flex-grow-1 overflow-auto p-3" style="min-height: 0">
                <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
                <div v-show="!showCenter" class="h-100">
                    <router-view :key="$route.fullPath" class="h-100" />
                </div>
            </div>
            <ChatPanel v-if="isBottomPanelOpen" />
        </div>
        <FlexPanel v-if="showPanels" ref="historyPanel" side="right" :reactive-width.sync="historyPanelWidth">
            <template v-slot:closed-button="{ open }">
                <GButton class="history-expand-button" size="small" @click="open">
                    <FontAwesomeIcon fixed-width :icon="faChevronLeft" />
                    <transition name="slide">
                        <span>History</span>
                    </transition>
                </GButton>
            </template>
            <HistoryIndex @show="onShow" />
        </FlexPanel>
        <FlexPanel
            v-if="showPanels && isRightPanelOpen"
            panel-id="chat-panel"
            side="right"
            :reactive-width.sync="chatPanelWidth">
            <ChatGXY
                :exchange-id="activeChatId || undefined"
                docked
                @close="chatStore.hideChat()"
                @undock="handleUndock" />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>

<style scoped lang="scss">
.history-expand-button {
    display: flex;
    align-items: center;
    height: 1.6rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    position: absolute;
    top: 0;
    right: 0;
    z-index: 100;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;

    span {
        opacity: 0;
        max-width: 0;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    &:hover span {
        opacity: 1;
        max-width: 100px;
    }
}

// Slide transition for History text
.slide-enter-active,
.slide-leave-active {
    transition: all 0.3s ease;
    overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
    opacity: 0;
    transform: translateX(10px);
    max-width: 0;
}

.slide-enter-to,
.slide-leave-from {
    opacity: 1;
    transform: translateX(0);
    max-width: 100px;
}
</style>
