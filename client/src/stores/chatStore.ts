import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

export type ChatLocation = "center" | "right" | "bottom";

export const useChatStore = defineStore("chatStore", () => {
    const chatLocation = useUserLocalStorage<ChatLocation>("chat-location", "center");
    const chatVisible = useUserLocalStorage("chat-visible", false);
    const activeChatId = ref<string | null>(null);

    const isRightPanelOpen = computed(() => chatLocation.value === "right" && chatVisible.value);
    const isBottomPanelOpen = computed(() => chatLocation.value === "bottom" && chatVisible.value);
    const isCenterMode = computed(() => chatLocation.value === "center");

    function showChat(chatId?: string | null) {
        if (chatId !== undefined) {
            activeChatId.value = chatId;
        }
        chatVisible.value = true;
    }

    function hideChat() {
        chatVisible.value = false;
    }

    function toggleChat() {
        chatVisible.value = !chatVisible.value;
    }

    function setLocation(loc: ChatLocation) {
        chatLocation.value = loc;
    }

    function setActiveChatId(id: string | null) {
        activeChatId.value = id;
    }

    return {
        chatLocation,
        chatVisible,
        activeChatId,
        isRightPanelOpen,
        isBottomPanelOpen,
        isCenterMode,
        showChat,
        hideChat,
        toggleChat,
        setLocation,
        setActiveChatId,
    };
});
