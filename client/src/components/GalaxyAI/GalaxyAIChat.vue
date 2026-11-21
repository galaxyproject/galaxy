<script setup lang="ts">
import { storeToRefs } from "pinia";

import { useChatStore } from "@/stores/chatStore";

import PluginChat from "./PluginChat.vue";
import GalaxyAI from "@/components/GalaxyAI.vue";

const props = defineProps<{
    source: "docked" | "panel" | "center";
    exchangeId?: string;
    initialQuestion?: string;
    compact?: boolean;
}>();

const { chatPlugin } = storeToRefs(useChatStore());
</script>

<template>
    <PluginChat
        v-if="chatPlugin"
        :source="props.source"
        :exchange-id="props.exchangeId"
        :initial-question="props.initialQuestion" />
    <GalaxyAI
        v-else-if="chatPlugin === null"
        :exchange-id="props.exchangeId"
        :initial-question="props.initialQuestion"
        :compact="props.compact"
        :docked="props.source === 'docked'"
        :panel="props.source === 'panel'" />
</template>
