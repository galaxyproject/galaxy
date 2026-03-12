import { defineStore } from "pinia";
import { ref } from "vue";

export const useChatStore = defineStore("chatStore", () => {
    const isDockedPanelOpen = ref(false);
    const dockedChatId = ref<string | null>(null);

    function openDockedPanel(chatId: string | null = null) {
        isDockedPanelOpen.value = true;
        dockedChatId.value = chatId;
    }

    function closeDockedPanel() {
        isDockedPanelOpen.value = false;
        dockedChatId.value = null;
    }

    function setDockedChatId(chatId: string | null) {
        dockedChatId.value = chatId;
    }

    return {
        isDockedPanelOpen,
        dockedChatId,
        openDockedPanel,
        closeDockedPanel,
        setDockedChatId,
    };
});
