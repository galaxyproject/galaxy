<script setup lang="ts">
import { faCheck, faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { nextTick, onUnmounted, ref, watch } from "vue";

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

/** Briefly shown after a successful save (independent of `props.hasChanges`) when the exposed `flashSavedIndicator` method is called. */
const showSavedIndicator = ref(false);

let savedIndicatorTimeout: ReturnType<typeof setTimeout> | undefined;
onUnmounted(() => clearTimeout(savedIndicatorTimeout));

/** Flashes a "Saved" indicator when called, given `props.hasChanges` is `false`. */
async function flashSavedIndicator() {
    clearTimeout(savedIndicatorTimeout);

    // If `props.hasChanges` becoming false and this call happen at the same time, wait a tick
    // so the "Saved" indicator doesn't flash in and out immediately.
    await nextTick();
    showSavedIndicator.value = true;
    savedIndicatorTimeout = setTimeout(() => {
        showSavedIndicator.value = false;
    }, 1500);
}

// If changes come back in while the "Saved" indicator is showing, dismiss it right
// away and cancel the pending timeout, so it can't flash back in once hasChanges clears again.
watch(
    () => props.hasChanges,
    (hasChanges) => {
        if (hasChanges) {
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
    <div class="changes-indicator small text-muted unselectable">
        <span
            v-if="props.hasChanges"
            class="changes-unsaved-indicator"
            :data-description="`${props.objectNamespace} unsaved indicator`">
            <FontAwesomeIcon :icon="faInfoCircle" size="lg" />
            Unsaved
        </span>

        <transition v-if="!props.hasChanges" name="saved-indicator">
            <span v-show="showSavedIndicator" class="changes-saved-indicator">
                <FontAwesomeIcon :icon="faCheck" fixed-width />
                Saved
            </span>
        </transition>
    </div>
</template>

<style scoped lang="scss">
.changes-indicator {
    display: flex;
    gap: 0.5rem;
    align-items: center;

    .changes-unsaved-indicator {
        color: var(--color-orange-600);
    }

    .changes-saved-indicator {
        color: var(--color-green-500);
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
}
</style>
