import { defineStore, storeToRefs } from "pinia";
import { computed, ref, shallowRef } from "vue";

import { GalaxyApi } from "@/api/client";
import type { ChatCommand } from "@/components/GalaxyAI/chatPlugin";
import type { ChatHistoryItem } from "@/components/GalaxyAI/chatTypes";
import { Toast } from "@/composables/toast";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

export type ChatLocation = "center" | "right" | "bottom";

export const useChatStore = defineStore("chatStore", () => {
    const chatLocation = useUserLocalStorage<ChatLocation>("chat-location", "center");
    const chatVisible = useUserLocalStorage("chat-visible", false);
    const cachedActiveChatId = useUserLocalStorage<string>("active-chat-id", "");
    const chatHistory = ref<ChatHistoryItem[]>([]);
    const loading = ref(false);
    const newChatRequestCount = ref(0);

    const { config, isLoaded } = storeToRefs(useConfigStore());
    const { currentUser, isAnonymous } = storeToRefs(useUserStore());

    /** Null for Galaxy's own chat, undefined until known */
    const chatPlugin = computed(() => {
        let plugin: string | null | undefined;
        if (isLoaded.value) {
            const configured: string | null = config.value?.ai_chat_plugin || null;
            if (!configured) {
                plugin = null;
            } else if (currentUser.value) {
                plugin = isAnonymous.value ? null : configured;
            }
        }
        return plugin;
    });
    const chatSlot = shallowRef<HTMLElement | null>(null);
    const reportedChatId = ref<string | null>(null);
    const chatCommands = ref<ChatCommand[]>([]);
    const agentState = ref<"loading" | "ready" | "failed">("loading");
    const unsaved = ref(false);

    const isRightPanelOpen = computed(() => chatLocation.value === "right" && chatVisible.value);
    const isBottomPanelOpen = computed(() => chatLocation.value === "bottom" && chatVisible.value);
    const isCenterMode = computed(() => chatLocation.value === "center");

    const activeChatId = computed({
        get: () => (chatPlugin.value ? reportedChatId.value : cachedActiveChatId.value || null),
        set: (id: string | null) => {
            if (!chatPlugin.value) {
                cachedActiveChatId.value = id || "";
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

        const { data, error } =
            pageId && !chatPlugin.value
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

    function openChat(id: string) {
        let accepted = true;
        if (chatPlugin.value) {
            const replacing = reportedChatId.value !== id || chatCommands.value.length > 0;
            accepted = !replacing || mayReplace();
            if (replacing && accepted) {
                chatCommands.value.push({ type: "open", exchange_id: id });
            }
        } else {
            setActiveChatId(id);
        }
        return accepted;
    }

    function askChat(question: string) {
        const accepted = mayReplace();
        if (accepted) {
            chatCommands.value.push({ type: "ask", question });
        }
        return accepted;
    }

    function mayReplace() {
        return !unsaved.value || window.confirm("This chat has unsaved changes, which may be lost. Continue?");
    }

    function takeCommands() {
        let taken: ChatCommand[] = [];
        if (agentState.value === "ready") {
            taken = chatCommands.value;
            chatCommands.value = [];
        }
        return taken;
    }

    function pluginShows(id: string | null) {
        reportedChatId.value = id;
        if (id && !chatHistory.value.some((item) => item.id === id)) {
            loadHistory().catch((e) => Toast.error(errorMessageAsString(e), "Failed to load chat history"));
        }
    }

    function agentSilent() {
        if (agentState.value === "loading") {
            agentState.value = "failed";
        }
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
        agentSilent,
        agentState,
        askChat,
        chatCommands,
        chatPlugin,
        chatSlot,
        openChat,
        pluginShows,
        takeCommands,
        unsaved,
    };
});
