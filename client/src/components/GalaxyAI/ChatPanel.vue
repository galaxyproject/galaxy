<script setup lang="ts">
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { useChatStore } from "@/stores/chatStore";

import ChatActions from "./ChatActions.vue";
import GalaxyAI from "@/components/GalaxyAI.vue";

const chatStore = useChatStore();
const { activeChatId } = storeToRefs(chatStore);

const route = useRoute();
const router = useRouter();

const collapsed = ref(false);

function dockTo(location: "right" | "bottom") {
    chatStore.dockChat(location, activeChatId.value);
    if (route.path.startsWith("/galaxyai")) {
        router.push("/");
    }
}

// Expand collapsed panel if a chat is selected from the sidebar
watch(
    activeChatId,
    (chatId) => {
        if (chatId && collapsed.value) {
            collapsed.value = false;
        }
    },
    { immediate: true },
);
</script>

<template>
    <div class="chat-panel" :class="collapsed ? 'collapsed' : 'expanded'">
        <div class="chat-panel-header">
            <span class="chat-panel-title">GalaxyAI</span>
            <ChatActions source="panel" :collapsed.sync="collapsed" @dock-to="dockTo" />
        </div>
        <div v-show="!collapsed" class="chat-panel-body">
            <GalaxyAI :exchange-id="activeChatId || undefined" panel />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.chat-panel {
    flex-shrink: 0;
    border-top: $border-default;
}

.chat-panel.expanded {
    height: 50vh;
    display: flex;
    flex-direction: column;
}

.chat-panel-header {
    padding: 0.5rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: $panel-bg-color;
    user-select: none;
}

.chat-panel-title {
    font-weight: 600;
    font-size: 0.85rem;
}

.chat-panel-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
}
</style>
