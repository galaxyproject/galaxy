<script setup lang="ts">
import { faChevronDown, faChevronUp, faExpand, faExternalLinkAlt, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { ref } from "vue";
import { useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import { useChatStore } from "@/stores/chatStore";

import ChatGXY from "@/components/ChatGXY.vue";

const router = useRouter();
const chatStore = useChatStore();
const { activeChatId } = storeToRefs(chatStore);

const collapsed = ref(false);

function maximize() {
    const path = activeChatId.value ? `/chatgxy/${activeChatId.value}` : "/chatgxy";
    chatStore.setLocation("center");
    chatStore.hideChat();
    router.push(path);
}

function popOut() {
    const Galaxy = getGalaxyInstance();
    const id = activeChatId.value;
    const path = id ? `/chatgxy/${id}` : "/chatgxy";
    Galaxy.frame.add({ title: "ChatGXY", url: `${path}?compact=true` });
    chatStore.hideChat();
}

function close() {
    chatStore.hideChat();
}
</script>

<template>
    <div class="chat-panel" :class="collapsed ? 'collapsed' : 'expanded'">
        <div class="chat-panel-header">
            <span class="chat-panel-title">ChatGXY</span>
            <div class="chat-panel-actions">
                <button class="chat-panel-btn" title="Open full view" @click="maximize">
                    <FontAwesomeIcon :icon="faExpand" fixed-width />
                </button>
                <button class="chat-panel-btn" title="Open in floating window" @click="popOut">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                </button>
                <button class="chat-panel-btn" title="Toggle panel" @click="collapsed = !collapsed">
                    <FontAwesomeIcon :icon="collapsed ? faChevronUp : faChevronDown" fixed-width />
                </button>
                <button class="chat-panel-btn" title="Close panel" @click="close">
                    <FontAwesomeIcon :icon="faTimes" fixed-width />
                </button>
            </div>
        </div>
        <div v-show="!collapsed" class="chat-panel-body">
            <ChatGXY :exchange-id="activeChatId || undefined" panel />
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

.chat-panel-actions {
    display: flex;
    gap: 0.25rem;
}

.chat-panel-btn {
    background: none;
    border: none;
    padding: 0.25rem 0.4rem;
    cursor: pointer;
    color: $text-muted;
    border-radius: 0.25rem;

    &:hover {
        color: $text-color;
        background: rgba(0, 0, 0, 0.06);
    }
}

.chat-panel-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
}
</style>
