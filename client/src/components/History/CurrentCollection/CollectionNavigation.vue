<script setup lang="ts">
import { faAngleDoubleLeft, faAngleLeft } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { CollectionEntry } from "@/api";

import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    historyName: string;
    selectedCollections: CollectionEntry[];
}

const props = defineProps<Props>();

const emit = defineEmits(["update:selected-collections"]);

const previousName = computed(() => {
    const length = props.selectedCollections.length;

    if (length > 1) {
        const last = props.selectedCollections[length - 2];
        return last?.name;
    }

    return null;
});

function back() {
    const newList = props.selectedCollections.slice(0, -1);
    emit("update:selected-collections", newList);
}

function close() {
    emit("update:selected-collections", []);
}
</script>

<template>
    <div class="mx-1 mt-1">
        <GButton
            v-g-tooltip:hover="historyName"
            size="small"
            class="text-left text-decoration-none overflow-hidden text-nowrap w-100"
            style="text-overflow: ellipsis"
            transparent
            color="blue"
            @click="close">
            <FontAwesomeIcon :icon="faAngleDoubleLeft" class="mr-1" data-description="back to history" fixed-width />
            <span> History: {{ historyName }} </span>
        </GButton>

        <GButton v-if="previousName" size="small" class="text-decoration-none" transparent color="blue" @click="back">
            <FontAwesomeIcon :icon="faAngleLeft" class="mr-1" fixed-width />
            <span>{{ previousName }}</span>
        </GButton>
    </div>
</template>
