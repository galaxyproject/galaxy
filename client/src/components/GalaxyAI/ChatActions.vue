<script setup lang="ts">
import {
    faAngleDoubleDown,
    faChevronDown,
    faChevronUp,
    faColumns,
    faExpand,
    faExternalLinkAlt,
    faList,
    faPlus,
    faTimes,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { getGalaxyInstance } from "@/app";
import { useActivityStore } from "@/stores/activityStore.js";
import { useChatStore } from "@/stores/chatStore";

import GButton from "../BaseComponents/GButton.vue";

const props = defineProps<{
    source: "docked" | "panel" | "center";
    collapsed?: boolean;
    enableDelete?: boolean;
}>();

const emit = defineEmits<{
    (e: "delete"): void;
    (e: "dock-to", location: "right" | "bottom"): void;
    (e: "update:collapsed", value: boolean): void;
}>();

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const activityStore = useActivityStore("default");

const showingActivityPanel = computed(() => activityStore.toggledSideBar === "galaxyai");

function startNew() {
    if (props.source === "center") {
        router.push("/galaxyai/new");
    } else {
        chatStore.showChat(null);
    }
    emit("update:collapsed", false);
}

function maximize() {
    const chatId = chatStore.activeChatId;
    chatStore.setLocation("center");
    chatStore.hideChat();
    router.push(chatId ? `/galaxyai/${chatId}` : "/galaxyai");
}

function popOut() {
    // If opening window manager chat from center or docked mode, we want to set the center/dock
    // to a new chat and then open the current chat in the window manager, so we don't have the
    // same chat open in two places
    const id = props.source === "center" ? route.params["exchangeId"] || null : chatStore.activeChatId;
    const path = id ? `/galaxyai/${id}` : "/galaxyai/new";
    getGalaxyInstance().frame.add({ title: "GalaxyAI", url: `${path}?compact=true` });

    if (props.source === "center") {
        router.push("/galaxyai/new");
    } else if (props.source === "docked") {
        chatStore.setActiveChatId(null);
        chatStore.hideChat();
    } else {
        chatStore.hideChat();
    }
}

function onDockTo(location: "right" | "bottom") {
    emit("dock-to", location);
}
</script>

<template>
    <div class="chat-panel-actions">
        <GButton
            size="small"
            transparent
            outline
            :pressed="showingActivityPanel"
            :title="showingActivityPanel ? 'Hide Chats Panel' : 'Show Chats Panel'"
            @click="activityStore.toggleSideBar('galaxyai')">
            <FontAwesomeIcon :icon="faList" fixed-width />
            <span class="btn-label">
                <span v-if="showingActivityPanel">Hide</span>
                <span v-else>Show</span>
                Chats
            </span>
        </GButton>
        <GButton data-description="new chat button" size="small" transparent title="Start New Chat" @click="startNew">
            <FontAwesomeIcon :icon="faPlus" fixed-width />
            <span class="btn-label">New</span>
        </GButton>
        <GButton
            v-if="(props.source === 'center' || props.source === 'docked') && !props.collapsed"
            data-description="delete chat button"
            :disabled="!props.enableDelete"
            size="small"
            transparent
            title="Delete this conversation"
            @click="emit('delete')">
            <FontAwesomeIcon :icon="faTrash" fixed-width />
        </GButton>
        <GButton
            v-if="props.source !== 'center'"
            size="small"
            transparent
            title="Open in center view"
            @click="maximize">
            <FontAwesomeIcon :icon="faExpand" fixed-width />
        </GButton>
        <template v-if="props.source === 'center'">
            <GButton size="small" transparent title="Dock to side panel" @click="onDockTo('right')">
                <FontAwesomeIcon :icon="faColumns" fixed-width />
            </GButton>
            <GButton size="small" transparent title="Dock to bottom panel" @click="onDockTo('bottom')">
                <FontAwesomeIcon :icon="faAngleDoubleDown" fixed-width />
            </GButton>
        </template>
        <GButton size="small" transparent title="Open in floating window" @click="popOut">
            <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
        </GButton>
        <GButton
            v-if="props.source === 'panel'"
            size="small"
            transparent
            title="Toggle panel"
            @click="emit('update:collapsed', !props.collapsed)">
            <FontAwesomeIcon :icon="props.collapsed ? faChevronUp : faChevronDown" fixed-width />
        </GButton>
        <GButton
            v-if="props.source !== 'center'"
            size="small"
            transparent
            title="Close panel"
            @click="chatStore.hideChat()">
            <FontAwesomeIcon :icon="faTimes" fixed-width />
        </GButton>
    </div>
</template>

<style scoped>
.chat-panel-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.25rem;
}

@container (max-width: 440px) {
    .btn-label {
        display: none;
    }
}
</style>
