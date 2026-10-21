<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { nextTick, onUnmounted, ref, watch } from "vue";

import localize from "@/utils/localization";

import CheckDraw from "@/components/Common/SuccessIndicator/CheckDraw.vue";

interface Props {
    /** If the object has unsaved changes */
    hasChanges: boolean;
    /**
     * Optional namespace for the object being saved
     * @default "item"
     */
    objectNamespace?: string;
}

const props = withDefaults(defineProps<Props>(), {
    objectNamespace: "item",
});

/** Briefly shown after a successful save when the exposed `flashSavedIndicator` method is called. */
const showSavedIndicator = ref(false);

/** Used to key each individual flash so `CheckDraw` replays its draw-in animation each time. */
const flashKey = ref(0);

let savedIndicatorTimeout: ReturnType<typeof setTimeout> | undefined;
let unmounted = false;

onUnmounted(() => {
    unmounted = true;
    flashKey.value++;
    clearTimeout(savedIndicatorTimeout);
});

/** Flashes a "Saved" indicator when called, given `props.hasChanges` is `false`. */
async function flashSavedIndicator() {
    const generation = ++flashKey.value;
    clearTimeout(savedIndicatorTimeout);

    // Let a simultaneous `hasChanges` update settle before deciding whether the feedback is still valid.
    await nextTick();
    if (unmounted || generation !== flashKey.value || props.hasChanges) {
        return;
    }
    showSavedIndicator.value = true;
    savedIndicatorTimeout = setTimeout(() => {
        if (!unmounted && generation === flashKey.value) {
            showSavedIndicator.value = false;
        }
    }, 1500);
}

// If changes come back in while the "Saved" indicator is showing, dismiss it right
// away and cancel the pending timeout, so it can't flash back in once hasChanges clears again.
watch(
    () => props.hasChanges,
    (hasChanges) => {
        if (hasChanges) {
            flashKey.value++;
            clearTimeout(savedIndicatorTimeout);
            showSavedIndicator.value = false;
        }
    },
);

defineExpose({
    flashSavedIndicator,
});
</script>

<template>
    <span class="changes-indicator small text-muted unselectable" role="status" aria-live="polite" aria-atomic="true">
        <span
            v-if="props.hasChanges"
            class="changes-unsaved-indicator"
            :data-description="`${props.objectNamespace} unsaved indicator`">
            <FontAwesomeIcon :icon="faInfoCircle" size="lg" aria-hidden="true" />
            {{ localize("Unsaved") }}
        </span>

        <transition v-if="!props.hasChanges" name="saved-indicator">
            <span
                v-show="showSavedIndicator"
                class="changes-saved-indicator"
                :data-description="`${props.objectNamespace} saved indicator`">
                <CheckDraw v-if="showSavedIndicator" :key="flashKey" />
                {{ localize("Saved") }}
            </span>
        </transition>
    </span>
</template>

<style scoped lang="scss">
.changes-indicator {
    display: inline-flex;
    gap: 0.5rem;
    align-items: center;

    .changes-unsaved-indicator {
        color: var(--color-orange-700);
    }

    .changes-saved-indicator {
        color: var(--color-green-700);
        display: flex;
        gap: 0.25rem;
        align-items: center;
    }

    .saved-indicator-enter-active,
    .saved-indicator-leave-active {
        transition:
            opacity 0.2s ease,
            transform 0.2s ease;
    }

    // TODO(vue3): rename .saved-indicator-enter to .saved-indicator-enter-from
    .saved-indicator-enter,
    .saved-indicator-leave-to {
        opacity: 0;
        transform: translateY(-2px);
    }

    @media (prefers-reduced-motion: reduce) {
        .saved-indicator-enter-active,
        .saved-indicator-leave-active {
            transition: none;
        }

        .saved-indicator-enter,
        .saved-indicator-leave-to {
            transform: none;
        }
    }
}
</style>
