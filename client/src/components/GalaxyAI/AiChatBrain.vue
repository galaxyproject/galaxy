<script setup lang="ts">
import axios from "axios";
import { storeToRefs } from "pinia";
import { onBeforeUnmount, ref, watch } from "vue";

import { getAppRoot } from "@/onload/loadConfig";
import { useChatStore } from "@/stores/chatStore";

import { activeChat, chatConfig, commandMessage, importPlugin } from "./chatPlugin";

/** Hosts the chat plugin's element and moves it to whichever place shows the chat. */
const props = defineProps<{ plugin: string }>();

const READY_TIMEOUT = 30000;

const chatStore = useChatStore();
const { agentState, chatCommands, chatSlot } = storeToRefs(chatStore);

const parking = ref<HTMLElement | null>(null);
let element: HTMLElement | undefined;
let starting = false;
let ended = false;
let readyTimer: ReturnType<typeof setTimeout> | undefined;

function onReport(event: Event) {
    const message = (event as CustomEvent).detail;
    agentState.value = "ready";
    if (message?.visualization_saved !== undefined) {
        chatStore.unsaved = !message.visualization_saved;
    }
    const exchangeId = activeChat(message?.visualization_config);
    if (exchangeId !== undefined) {
        chatStore.pluginShows(exchangeId);
    }
}

watch(
    [agentState, () => chatCommands.value.length],
    () => {
        if (element) {
            for (const command of chatStore.takeCommands()) {
                element.dispatchEvent(new CustomEvent("galaxy", { detail: commandMessage(command) }));
            }
        }
    },
    { flush: "sync" },
);

async function start() {
    const { data } = await axios.get(`${getAppRoot()}api/plugins/${props.plugin}`);
    const tag = data?.entry_point?.attr?.webcomponent;
    if (tag) {
        await importPlugin(`${data.href}/${data.entry_point.attr.src}`);
    } else {
        throw new Error(`The chat plugin ${props.plugin} declares no webcomponent.`);
    }
    if (!ended) {
        const created = document.createElement(tag);
        created.className = "d-block h-100 w-100";
        created.setAttribute(
            "data-incoming",
            JSON.stringify({
                root: window.location.origin + getAppRoot(),
                visualization_config: chatConfig(chatCommands.value.shift()),
                visualization_plugin: data,
            }),
        );
        created.addEventListener("galaxy-visualization", onReport);
        element = created;
        readyTimer = setTimeout(() => chatStore.agentSilent(), READY_TIMEOUT);
        place();
    }
}

function place() {
    if (chatSlot.value && !starting) {
        starting = true;
        start().catch((e) => {
            console.error(e);
            chatStore.agentSilent();
        });
    }
    const target = chatSlot.value ?? parking.value;
    if (element && target && element.parentElement !== target) {
        target.appendChild(element);
    }
}

watch([chatSlot, parking], place, { immediate: true });

onBeforeUnmount(() => {
    ended = true;
    clearTimeout(readyTimer);
    element?.remove();
});
</script>

<template>
    <div ref="parking" class="d-none" />
</template>
