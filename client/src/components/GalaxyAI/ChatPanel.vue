<script setup lang="ts">
import { faPen } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { useChatStore } from "@/stores/chatStore";

import ChatActions from "./ChatActions.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import RenameModal from "@/components/Common/RenameModal.vue";
import GalaxyAI from "@/components/GalaxyAI.vue";

const chatStore = useChatStore();
const { activeChatId, activeChatName } = storeToRefs(chatStore);

const route = useRoute();
const router = useRouter();

const collapsed = ref(false);
const showRename = ref(false);

async function renameChat(_newName: string): Promise<void> {
    // TODO: call API to persist the new name on the chat exchange
}

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
            <div class="chat-panel-title-group">
                <span class="chat-panel-title">GalaxyAI</span>
                <span v-if="activeChatName" class="chat-panel-chat-name">{{ activeChatName }}</span>
                <GButton v-if="activeChatId" inline transparent title="Rename this chat" @click="showRename = true">
                    <FontAwesomeIcon :icon="faPen" />
                </GButton>
            </div>
            <ChatActions source="panel" :collapsed.sync="collapsed" @dock-to="dockTo" />
        </div>

        <RenameModal
            v-if="showRename"
            item-type="chat"
            :name="activeChatName ?? ''"
            :rename-action="renameChat"
            @close="showRename = false" />
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
    min-width: 0;
}

.chat-panel-title-group {
    display: flex;
    align-items: baseline;
    gap: 0.4em;
    min-width: 0;
    overflow: hidden;
    flex-shrink: 1;
}

.chat-panel-title {
    font-weight: 600;
    font-size: 0.85rem;
    white-space: nowrap;
    flex-shrink: 0;
}

.chat-panel-chat-name {
    font-size: 0.75rem;
    font-weight: 400;
    color: var(--gray-light, #888);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
}

.chat-panel-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
}
</style>
