<script setup lang="ts">
import { storeToRefs } from "pinia";
import { ref } from "vue";

import { useChatStore } from "@/stores/chatStore";

import ChatActions from "./ChatActions.vue";
import GalaxyAI from "@/components/GalaxyAI.vue";

const chatStore = useChatStore();
const { activeChatId } = storeToRefs(chatStore);

const collapsed = ref(false);
</script>

<template>
    <div class="chat-panel" :class="collapsed ? 'collapsed' : 'expanded'">
        <div class="chat-panel-header">
            <span class="chat-panel-title">GalaxyAI</span>
            <ChatActions source="panel" :collapsed.sync="collapsed" />
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
