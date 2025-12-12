<script setup lang="ts">
import { computed } from "vue";

import { useMarkdown } from "@/composables/markdown";

interface Props {
    /** Single tip message or array of tip messages. Supports markdown formatting. */
    tips?: string | string[];
    /** Visual variant of the tip box */
    variant?: "info" | "warning" | "success" | "danger";
}

const props = withDefaults(defineProps<Props>(), {
    tips: undefined,
    variant: "info",
});

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const tipList = computed(() => {
    if (!props.tips) {
        return [];
    }
    const tips = Array.isArray(props.tips) ? props.tips : [props.tips];
    return tips.map((tip) => renderMarkdown(tip));
});

const variantClass = computed(() => `tip-${props.variant}`);
</script>

<template>
    <div v-if="tipList.length > 0" class="g-tip" :class="variantClass">
        <small class="text-muted">
            <span v-for="(tip, index) in tipList" :key="index" class="tip-item">
                <strong>Tip:</strong>
                <!-- This is rendered markdown safe to use in Vue templates. -->
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span v-html="tip"></span>
            </span>
        </small>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.g-tip {
    padding: 0.5rem 0.75rem;
    background-color: $gray-100;
    border-radius: $border-radius-base;
    border-left: 3px solid $brand-primary;

    &.tip-info {
        background-color: $gray-100;
        border-left-color: $brand-primary;
    }

    &.tip-warning {
        background-color: scale-color($brand-warning, $lightness: +75%);
        border-left-color: $brand-warning;
    }

    &.tip-success {
        background-color: scale-color($brand-success, $lightness: +75%);
        border-left-color: $brand-success;
    }

    &.tip-danger {
        background-color: scale-color($brand-danger, $lightness: +75%);
        border-left-color: $brand-danger;
    }
}

.tip-item {
    strong {
        margin-right: 0.25rem;
    }

    &:not(:last-child)::after {
        content: " ";
        display: block;
        margin-bottom: 0.25rem;
    }
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
