<script setup lang="ts">
import { faArrowRight, faCheck, faPlay, faSpinner, faSquare, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { createPopper } from "@popperjs/core";
import { computed, ref, watch } from "vue";

import type { TourStep } from "@/api/tours";

import GButton from "../BaseComponents/GButton.vue";

const props = defineProps<{
    step: TourStep;
    isPlaying: boolean;
    isLast: boolean;
    waitingOnElement?: string | null;
}>();

const emit = defineEmits<{
    (e: "end"): void;
    (e: "next"): void;
    (e: "play", value: boolean): void;
}>();

const targetElement = computed(() => {
    if (props.step.element) {
        return document.querySelector(props.step.element);
    }
    return null;
});

const targetElementVisible = computed(() => {
    const el = targetElement.value;
    if (el) {
        const rect = el.getBoundingClientRect();
        return rect && rect.width > 0 && rect.height > 0;
    }
    return false;
});

const tourElement = ref<HTMLElement | null>(null);
watch(
    () => tourElement.value,
    () => {
        if (tourElement.value) {
            createStep();
        }
    },
    { immediate: true },
);

function createStep() {
    if (targetElement.value && targetElementVisible.value && tourElement.value) {
        createPopper(targetElement.value, tourElement.value, {
            modifiers: [
                {
                    name: "preventOverflow",
                    options: {
                        altAxis: true,
                        tether: false,
                        padding: 20,
                    },
                },
            ],
            strategy: "absolute",
            placement: "auto",
        });
    }
}
</script>

<template>
    <div
        ref="tourElement"
        class="tour-element"
        :class="{ 'tour-element-sticky': !targetElementVisible, 'tour-has-title': !!step.title }">
        <div v-if="step.title" class="tour-header">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="tour-title" v-html="step.title"></div>
        </div>
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div v-if="step.content" class="tour-content" v-html="step.content" />
        <div class="float-right p-2">
            <div>
                <template v-if="waitingOnElement && (isPlaying || !isLast)">
                    <GButton tooltip icon-only transparent :title="`Waiting for ${waitingOnElement}`">
                        <FontAwesomeIcon :icon="faSpinner" spin />
                    </GButton>
                </template>
                <template v-if="isLast">
                    <GButton class="tour-end" size="small" color="blue" @click.prevent="emit('end')">
                        <FontAwesomeIcon :icon="faCheck" />
                        Close
                    </GButton>
                </template>
                <template v-else-if="isPlaying">
                    <GButton class="tour-stop" size="small" color="blue" @click.prevent="emit('play', false)">
                        <FontAwesomeIcon :icon="faSquare" />
                        Stop Auto-Playing
                    </GButton>
                </template>
                <template v-else>
                    <GButton class="tour-end" size="small" color="blue" @click.prevent="emit('end')">
                        <FontAwesomeIcon :icon="faTimes" />
                        End Tour
                    </GButton>
                    <GButton class="tour-play" size="small" color="blue" @click.prevent="emit('play', true)">
                        <FontAwesomeIcon :icon="faPlay" />
                        Auto-Play Tour
                    </GButton>
                    <GButton class="tour-next" size="small" color="blue" @click.prevent="emit('next')">
                        <FontAwesomeIcon :icon="faArrowRight" />
                        Continue
                    </GButton>
                </template>
            </div>
        </div>
        <div v-if="targetElementVisible" class="tour-arrow" data-popper-arrow />
    </div>
</template>
