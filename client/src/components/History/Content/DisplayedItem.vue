<script setup lang="ts">
import { computed } from "vue";

import type { HistoryContentType } from "@/api/datasets";

import type { State } from "./model/states";

const props = defineProps<{
    deleted: boolean;
    hid: number;
    historyContentType: HistoryContentType;
    itemId: string;
    name: string;
    state: State;
}>();

const contentId = computed(() => `${props.historyContentType}-${props.itemId}`);
</script>

<template>
    <div :id="contentId" class="content-item rounded" :data-hid="props.hid" :data-state="props.state">
        <div class="p-1">
            <div class="d-flex">
                <span class="p-1" data-description="content item header info">
                    <span class="id hid">{{ props.hid }}: </span>
                    <span class="content-title name font-weight-bold">{{ props.name }}</span>
                </span>
            </div>
        </div>
    </div>
</template>
