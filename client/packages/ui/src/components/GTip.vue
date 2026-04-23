<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";

import { useMarkdown } from "../composables/markdown";

import type { ColorVariant } from "./componentVariants";

interface Props {
    /** List of tip messages. Supports markdown formatting. Must contain at least one entry. */
    tips: string[];

    /**
     * Automatically rotate tips every N milliseconds (0 = disabled).
     * @default 20000
     */
    autoRotateMs?: number;

    /**
     * Visual variant of the tip box
     * @default "info"
     */
    variant?: ColorVariant;
}

const props = withDefaults(defineProps<Props>(), {
    variant: "info",
    autoRotateMs: 20000,
});

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const tipList = computed(() => {
    return props.tips.map((tip) => renderMarkdown(tip));
});

// Start with a random tip
const currentIndex = ref(Math.floor(Math.random() * Math.max(props.tips.length, 1)));

const hasMultipleTips = computed(() => tipList.value.length > 1);
let rotateTimer: number | undefined;

function nextTip() {
    currentIndex.value = (currentIndex.value + 1) % tipList.value.length;
}

function prevTip() {
    currentIndex.value = (currentIndex.value - 1 + tipList.value.length) % tipList.value.length;
}

const variantClass = computed(() => `tip-${props.variant}`);

if (!props.tips.length) {
    console.warn("GTip component rendered with empty tips array");
}

// Auto-rotate tips if enabled
if (props.autoRotateMs > 0 && hasMultipleTips.value) {
    rotateTimer = window.setInterval(() => {
        nextTip();
    }, props.autoRotateMs);
}

onUnmounted(() => {
    if (rotateTimer) {
        clearInterval(rotateTimer);
    }
});
</script>

<template>
    <div v-if="tipList.length > 0" class="g-tip" :class="variantClass">
        <small class="text-muted tip-content" :class="{ 'has-controls': hasMultipleTips }">
            <span class="tip-item">
                <strong>Tip:</strong>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span v-html="tipList[currentIndex]"></span>
            </span>
        </small>

        <div v-if="hasMultipleTips" class="tip-controls">
            <button type="button" class="tip-nav" aria-label="Previous tip" @click="prevTip">‹</button>
            <span class="tip-counter">{{ currentIndex + 1 }} / {{ tipList.length }}</span>
            <button type="button" class="tip-nav" aria-label="Next tip" @click="nextTip">›</button>
        </div>
    </div>
</template>

<style scoped lang="scss">
.g-tip {
    position: relative;
    padding: 0.5rem 0.75rem;
    background-color: var(--color-grey-100);
    border-radius: 0.25rem;
    border-left: 3px solid var(--color-blue-600);

    &.tip-info {
        background-color: var(--color-grey-100);
        border-left-color: var(--color-blue-600);
    }

    &.tip-warning {
        background-color: var(--color-orange-200);
        border-left-color: var(--color-orange-600);
    }

    &.tip-success {
        background-color: var(--color-green-200);
        border-left-color: var(--color-green-600);
    }

    &.tip-danger {
        background-color: var(--color-red-200);
        border-left-color: var(--color-red-600);
    }
}

.tip-item {
    strong {
        margin-right: 0.25rem;
    }
}

.tip-content {
    display: block;

    &.has-controls {
        padding-right: 3.5rem; // reserve space for controls
    }
}

.tip-controls {
    position: absolute;
    right: 0.5rem;
    bottom: 0.25rem;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}

.tip-nav {
    background: none;
    border: none;
    padding: 0 0.25rem;
    cursor: pointer;
    color: inherit;
}

.tip-nav:hover {
    text-decoration: underline;
}

.tip-counter {
    font-size: 0.85em;
}

.tip-item :deep(p) {
    display: inline;
    margin: 0;
}

.tip-item :deep(code) {
    background-color: rgba(0, 0, 0, 0.05);
    padding: 0.125rem 0.25rem;
    border-radius: 3px;
    font-size: 0.9em;
}

.tip-item :deep(em) {
    font-style: italic;
}

.tip-item :deep(strong) {
    font-weight: 600;
}
</style>
