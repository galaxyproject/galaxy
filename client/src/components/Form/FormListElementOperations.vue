<script setup lang="ts">
import { faCaretDown, faCaretUp, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

interface Props {
    index: number;
    numElements: number;
    upButtonId: string;
    downButtonId: string;
    canDelete: boolean;
    deleteTooltip: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "delete"): void;
    (e: "swap-up"): void;
    (e: "swap-down"): void;
}>();
</script>

<template>
    <span class="float-right">
        <GButtonGroup>
            <GButton
                :id="upButtonId"
                tooltip
                tooltip-placement="bottom"
                title="move up"
                :disabled="index == 0"
                color="blue"
                transparent
                size="small"
                class="ml-0"
                @click="() => emit('swap-up')">
                <FontAwesomeIcon :icon="faCaretUp" />
            </GButton>
            <GButton
                :id="downButtonId"
                tooltip
                tooltip-placement="bottom"
                :disabled="index >= numElements - 1"
                title="move down"
                color="blue"
                transparent
                size="small"
                class="ml-0"
                @click="() => emit('swap-down')">
                <FontAwesomeIcon :icon="faCaretDown" />
            </GButton>
        </GButtonGroup>

        <GButton
            :disabled="!canDelete"
            tooltip
            tooltip-placement="bottom"
            :title="deleteTooltip"
            color="blue"
            transparent
            size="small"
            class="ml-0"
            @click="() => emit('delete')">
            <FontAwesomeIcon :icon="faTrashAlt" />
        </GButton>
    </span>
</template>
