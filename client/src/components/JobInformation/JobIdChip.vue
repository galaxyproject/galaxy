<script setup lang="ts">
import { ref, watch } from "vue";

import CopyToClipboard from "@/components/CopyToClipboard.vue";
import DecodedId from "@/components/DecodedId.vue";

const props = defineProps<{
    /** The encoded job ID to display. */
    id: string;
}>();

/** Briefly true right after `id` changes (e.g. paginating between jobs), to replay the reveal
 * animation on the short id text so the change is noticeable even if the text looks similar. */
const justChanged = ref(false);
let changeTimeout: ReturnType<typeof setTimeout> | undefined;
watch(
    () => props.id,
    (id, previousId) => {
        if (!id || !previousId || id === previousId) {
            return;
        }
        clearTimeout(changeTimeout);
        justChanged.value = true;
        changeTimeout = setTimeout(() => {
            justChanged.value = false;
        }, 900);
    },
);
</script>

<template>
    <span class="job-id-chip-container">
        <span class="job-id-chip">
            <span class="job-id-chip-value" :class="{ 'job-id-chip-value-reveal': justChanged }">{{ props.id }}</span>
            <DecodedId :id="props.id" />
            <CopyToClipboard
                message="Job API ID was copied to your clipboard"
                :text="props.id"
                title="Copy Job API ID" />
        </span>
    </span>
</template>

<style scoped lang="scss">
.job-id-chip-container {
    display: block;
    width: 100%;
    container-type: inline-size;
}

.job-id-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
    font-family: "JetBrains Mono", ui-monospace, monospace;
    font-size: clamp(0.4rem, 4.5cqi, var(--font-size-small));
    font-weight: 600;
    color: var(--color-blue-600);
    background: var(--color-blue-100);
    border: 0.07em solid var(--color-grey-200);
    border-radius: 999px;
    padding: 0.17em 0.69em;
    width: max-content;
    max-width: 100%;
    white-space: nowrap;

    :deep(svg) {
        font-size: 0.8em;
        color: var(--color-grey-500);

        &:hover {
            color: var(--color-blue-600);
        }
    }

    :deep(.g-button.g-medium) {
        font-size: inherit;
        padding: 0.1em;
        border-width: 0.07em !important;
        border-radius: 0.2em;
    }
}

.job-id-chip-value-reveal {
    display: inline-block;
    animation: job-id-chip-reveal 0.3s ease;
}

@keyframes job-id-chip-reveal {
    0% {
        opacity: 0;
        transform: translateY(-0.15em);
    }
    100% {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
