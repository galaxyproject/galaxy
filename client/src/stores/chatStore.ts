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
            setActiveChatId(chatId);
        }
        if (!chatVisible.value) {
            chatVisible.value = true;
        }
    }

    function hideChat() {
        if (chatVisible.value) {
            chatVisible.value = false;
        }
    }

    function toggleChat() {
        chatVisible.value = !chatVisible.value;
    }

    function setLocation(loc: ChatLocation) {
        if (chatLocation.value !== loc) {
            chatLocation.value = loc;
        }
    }

    function setActiveChatId(id: string | null) {
        if (activeChatId.value !== id) {
            activeChatId.value = id;
        }
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
