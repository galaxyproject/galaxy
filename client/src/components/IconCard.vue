<script setup lang="ts">
/** A generic Card, used as a template, that displays an action button,
 * an icon (font-awesome), along with a title and description.
 * Clicking the button emits an "onButtonClick" event. */

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { IconDefinition } from "font-awesome-6";
import type { PropType } from "vue";

type Sizes = "2xs" | "xs" | "sm" | "lg" | "xl" | "2xl" | `${number}x`;

const props = defineProps({
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        required: true,
    },
    icon: {
        type: Object as PropType<IconDefinition>,
        required: true,
    },
    iconSize: {
        type: String as PropType<Sizes>,
        default: "1x",
    },
    buttonText: {
        type: String,
        required: true,
    },
});

const emit = defineEmits<{
    (e: "onButtonClick"): void;
}>();

function onButtonClick() {
    emit("onButtonClick");
}
</script>

<template>
    <b-card :title="props.title" class="mx-4 icon-card">
        <b-container class="p-0">
            <b-row>
                <b-col>{{ props.description }}</b-col>
                <b-col cols="auto">
                    <FontAwesomeIcon :icon="props.icon" :size="props.iconSize" />
                </b-col>
            </b-row>
        </b-container>
        <b-button variant="primary" @click="onButtonClick">{{ props.buttonText }}</b-button>
    </b-card>
</template>

<style scoped>
.icon-card {
    max-width: 500px;
}
</style>
