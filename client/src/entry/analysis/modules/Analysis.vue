<script setup>
import { storeToRefs } from "pinia";
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { usePanels } from "@/composables/usePanels";
import { useChatStore } from "@/stores/chatStore";
import { useUserStore } from "@/stores/userStore";

import CenterFrame from "./CenterFrame.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import ChatGXY from "@/components/ChatGXY.vue";
import HistoryIndex from "@/components/History/Index.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import DragAndDropModal from "@/components/Upload/DragAndDropModal.vue";

const router = useRouter();
const showCenter = ref(false);
const { showPanels } = usePanels();

const historyPanel = ref(null);

const chatStore = useChatStore();
const { isDockedPanelOpen, dockedChatId } = storeToRefs(chatStore);
const { historyPanelWidth, chatPanelWidth } = storeToRefs(useUserStore());

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
    const chatId = dockedChatId.value;
    chatStore.closeDockedPanel();
    router.push(chatId ? `/chatgxy/${chatId}` : "/chatgxy");
}

// Close docked panel when navigating to /chatgxy center view
watch(
    () => router.currentRoute.path,
    (path) => {
        if (path.startsWith("/chatgxy")) {
            chatStore.closeDockedPanel();
        }
    },
);

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
        <div id="center" class="overflow-auto p-3 w-100">
            <CenterFrame v-show="showCenter" id="galaxy_main" @load="onLoad" />
            <div v-show="!showCenter" class="h-100">
                <router-view :key="$route.fullPath" class="h-100" />
            </div>
        </div>
        <FlexPanel v-if="showPanels" ref="historyPanel" side="right" :reactive-width.sync="historyPanelWidth">
            <HistoryIndex @show="onShow" />
        </FlexPanel>
        <FlexPanel
            v-if="showPanels && isDockedPanelOpen"
            panel-id="chat-panel"
            side="right"
            :reactive-width.sync="chatPanelWidth">
            <ChatGXY
                :exchange-id="dockedChatId || undefined"
                docked
                @close="chatStore.closeDockedPanel()"
                @undock="handleUndock" />
        </FlexPanel>
        <DragAndDropModal />
    </div>
</template>
