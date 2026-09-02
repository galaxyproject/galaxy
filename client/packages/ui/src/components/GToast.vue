<script setup lang="ts">
/**
 * Renders a global toast notification stack.
 *
 * A single instance is mounted near the application root. Toasts are pushed
 * onto a queue (see `composables/toast`) so any code can raise one without
 * importing this component directly.
 */

import {
    faCheckCircle,
    faExclamationCircle,
    faExclamationTriangle,
    faInfoCircle,
    faTimes,
    type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useRouter } from "vue-router/composables";

import { type ToastProps, useToast } from "../composables/toast";

import GButton from "./GButton.vue";

const { toasts, removeToast } = useToast();
const router = useRouter();

const variantIcon: Record<ToastProps["variant"], IconDefinition> = {
    success: faCheckCircle,
    info: faInfoCircle,
    warning: faExclamationTriangle,
    danger: faExclamationCircle,
};

function onClick(toast: ToastProps) {
    if (toast.to) {
        router.push(toast.to);
    } else if (toast.href) {
        window.location.href = toast.href;
    }
}
</script>

<template>
    <TransitionGroup tag="div" name="g-toast" class="g-toast-stack" aria-live="polite" aria-atomic="false">
        <div
            v-for="toast in toasts"
            :key="toast.id"
            class="g-toast"
            :class="[`g-toast-${toast.variant}`, { 'g-toast-clickable': toast.href || toast.to }]"
            role="alert"
            @click="onClick(toast)">
            <div class="g-toast-header">
                <div class="g-toast-title-section">
                    <FontAwesomeIcon :icon="variantIcon[toast.variant]" />
                    <strong v-if="toast.title">{{ toast.title }}</strong>
                </div>

                <GButton icon-only size="small" transparent @click.stop="removeToast(toast.id)">
                    <FontAwesomeIcon :icon="faTimes" />
                </GButton>
            </div>
            <div class="g-toast-body">{{ toast.message }}</div>
        </div>
    </TransitionGroup>
</template>

<style scoped lang="scss">
.g-toast-stack {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    z-index: 1100;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    width: 350px;
}

.g-toast {
    background-color: var(--color-grey-100);
    border: 1px solid var(--color-grey-300);
    border-left: 6px solid var(--color-blue-600);
    border-radius: 0.25rem;
    padding: 0.5rem 0.75rem;
    box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.1);

    &.g-toast-clickable:hover {
        cursor: pointer;
        background-color: var(--color-grey-200);
    }

    &.g-toast-success {
        border-left-color: var(--color-green-600);
    }
    &.g-toast-info {
        border-left-color: var(--color-blue-600);
    }
    &.g-toast-warning {
        border-left-color: var(--color-orange-600);
    }
    &.g-toast-danger {
        border-left-color: var(--color-red-600);
    }

    .g-toast-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.375rem;

        .g-toast-title-section {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
    }

    .g-toast-body {
        margin-top: 0.25rem;
    }
}

// Slide in from / out to the right; siblings ease into their new position.
.g-toast-enter-active,
.g-toast-leave-active,
.g-toast-move {
    transition:
        transform 0.3s ease,
        opacity 0.3s ease;
}

.g-toast-enter,
.g-toast-leave-to {
    opacity: 0;
    transform: translateX(110%);
}

// Take the leaving toast out of flow so the survivors collapse up smoothly.
.g-toast-leave-active {
    position: absolute;
    right: 0;
    width: 100%;
}

@media (prefers-reduced-motion) {
    .g-toast-enter-active,
    .g-toast-leave-active,
    .g-toast-move {
        transition: none;
    }

    .g-toast-enter,
    .g-toast-leave-to {
        transform: none;
    }
}
</style>
