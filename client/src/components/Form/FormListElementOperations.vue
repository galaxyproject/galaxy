<script setup lang="ts">
import { faCaretDown, faCaretUp, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";

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
        <BButtonGroup>
            <span v-b-tooltip.hover.bottom title="move up">
                <BButton
                    :id="upButtonId"
                    v-b-tooltip.hover.bottom
                    :disabled="index == 0"
                    role="button"
                    variant="link"
                    size="sm"
                    class="ml-0"
                    @click="() => emit('swap-up')">
                    <FontAwesomeIcon :icon="faCaretUp" />
                </BButton>
            </span>
            <span v-b-tooltip.hover.bottom title="move down">
                <BButton
                    :id="downButtonId"
                    :disabled="index >= numElements - 1"
                    title="move down"
                    role="button"
                    variant="link"
                    size="sm"
                    class="ml-0"
                    @click="() => emit('swap-down')">
                    <FontAwesomeIcon :icon="faCaretDown" />
                </BButton>
            </span>
        </BButtonGroup>

        <span v-b-tooltip.hover.bottom :title="deleteTooltip">
            <BButton
                :disabled="!canDelete"
                title="delete"
                role="button"
                variant="link"
                size="sm"
                class="ml-0"
                @click="() => emit('delete')">
                <FontAwesomeIcon :icon="faTrashAlt" />
            </BButton>
        </span>
    </span>
</template>
