<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faCaretUp, faTrashAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup } from "bootstrap-vue";

// @ts-ignore: bad library types
library.add(faTrashAlt, faCaretUp, faCaretDown);

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
            <BButton
                :id="upButtonId"
                v-b-tooltip.hover.bottom
                :disabled="index == 0"
                title="move up"
                role="button"
                variant="link"
                size="sm"
                class="ml-0"
                @click="() => emit('swap-up')">
                <FontAwesomeIcon icon="caret-up" />
            </BButton>
            <BButton
                :id="downButtonId"
                v-b-tooltip.hover.bottom
                :disabled="index >= numElements - 1"
                title="move down"
                role="button"
                variant="link"
                size="sm"
                class="ml-0"
                @click="() => emit('swap-down')">
                <FontAwesomeIcon icon="caret-down" />
            </BButton>
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
                <FontAwesomeIcon icon="trash-alt" />
            </BButton>
        </span>
    </span>
</template>
