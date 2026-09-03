<script setup lang="ts">
import { faCaretDown, faCaretUp, faCopy, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";

interface Props {
    index: number;
    numElements: number;
    upButtonId: string;
    downButtonId: string;
    cloneButtonId: string;
    canDelete: boolean;
    canClone: boolean;
    deleteTooltip: string;
    cloneTooltip: string;
}

defineProps<Props>();

const emit = defineEmits<{
    (e: "delete"): void;
    (e: "clone"): void;
    (e: "swap-up"): void;
    (e: "swap-down"): void;
}>();
</script>

<template>
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
            @click="() => emit('swap-down')">
            <FontAwesomeIcon :icon="faCaretDown" />
        </GButton>
        <GButton
            :id="cloneButtonId"
            :disabled="!canClone"
            tooltip
            tooltip-placement="bottom"
            :title="cloneTooltip"
            color="blue"
            transparent
            size="small"
            @click="() => emit('clone')">
            <FontAwesomeIcon :icon="faCopy" />
        </GButton>
        <GButton
            :disabled="!canDelete"
            tooltip
            tooltip-placement="bottom"
            :title="deleteTooltip"
            color="blue"
            transparent
            size="small"
            @click="() => emit('delete')">
            <FontAwesomeIcon :icon="faTrashAlt" />
        </GButton>
    </GButtonGroup>
</template>
