import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { GalaxyApi } from "@/api/client";
import type { ChatHistoryItem } from "@/components/GalaxyAI/chatTypes";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { rethrowSimple } from "@/utils/simple-error";

export type ChatLocation = "center" | "right" | "bottom";

export const useChatStore = defineStore("chatStore", () => {
    const chatLocation = useUserLocalStorage<ChatLocation>("chat-location", "center");
    const chatVisible = useUserLocalStorage("chat-visible", false);
    const cachedActiveChatId = useUserLocalStorage<string>("active-chat-id", "");
    const chatHistory = ref<ChatHistoryItem[]>([]);
    const loading = ref(false);
    const newChatRequestCount = ref(0);

    const isRightPanelOpen = computed(() => chatLocation.value === "right" && chatVisible.value);
    const isBottomPanelOpen = computed(() => chatLocation.value === "bottom" && chatVisible.value);
    const isCenterMode = computed(() => chatLocation.value === "center");

    const activeChatId = computed({
        get: () => cachedActiveChatId.value || null,
        set: (id: string | null) => {
            if (id) {
                cachedActiveChatId.value = id;
            } else {
                cachedActiveChatId.value = "";
            }
        },
    });

    function deleteChats(ids: Set<string>) {
        chatHistory.value = chatHistory.value.filter((item) => !ids.has(item.id));
        // If the chat currently in view was deleted, drop the reference so we don't
        // leave the UI pointing at a conversation that no longer exists.
        if (activeChatId.value && ids.has(activeChatId.value)) {
            activeChatId.value = null;
        }
    }

    async function deleteChatById(chatId: string) {
        if (!chatId) {
            return;
        }
        const { error } = await GalaxyApi().DELETE("/api/chat/exchange/{exchange_id}", {
            params: { path: { exchange_id: chatId } },
        });
        if (error) {
            rethrowSimple(error);
        }

        deleteChats(new Set([chatId]));
    }

    async function deleteChatsByIds(ids: Set<string>) {
        if (ids.size === 0) {
            return;
        }
        const { error } = await GalaxyApi().PUT("/api/chat/exchanges/batch/delete", {
            body: { ids: Array.from(ids) },
        });
        if (error) {
            rethrowSimple(error);
        }

        deleteChats(ids);
    }

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

    async function loadHistory(pageId?: string) {
        loading.value = true;

        const { data, error } = pageId
            ? await GalaxyApi().GET("/api/chat/page/{page_id}/history", {
                  params: { path: { page_id: pageId }, query: { limit: 50 } },
              })
            : await GalaxyApi().GET("/api/chat/history", {
                  params: { query: { limit: 50 } },
              });

        loading.value = false;

        if (error) {
            rethrowSimple(error);
        } else if (data) {
            chatHistory.value = data as unknown as ChatHistoryItem[];
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

    /** Ask chat surfaces to reset to a fresh conversation. A counter bump rather than
     * an id change, so the reset also fires for an unsaved conversation whose identity
     * (activeChatId / route param) wouldn't change. */
    function requestNewChat() {
        setActiveChatId(null);
        newChatRequestCount.value++;
    }

    /** Returns the active chat id, falling back to the most recent history item, or null. */
    function resolveDockChatId(): string | null {
        return activeChatId.value ?? chatHistory.value[0]?.id ?? null;
    }

    /** Sets the chat location and shows the chat with the given id in one step. */
    function dockChat(location: ChatLocation, chatId?: string | null) {
        setLocation(location);
        showChat(chatId);
    }

    return {
        chatHistory,
        chatLocation,
        chatVisible,
        activeChatId,
        isRightPanelOpen,
        isBottomPanelOpen,
        isCenterMode,
        deleteChatById,
        deleteChats,
        deleteChatsByIds,
        showChat,
        hideChat,
        loadHistory,
        loading,
        newChatRequestCount,
        requestNewChat,
        toggleChat,
        setLocation,
        setActiveChatId,
        resolveDockChatId,
        dockChat,
    };
});
