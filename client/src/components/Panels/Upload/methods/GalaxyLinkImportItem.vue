<script setup lang="ts">
import type { UploadStatus } from "@/composables/upload/uploadItemTypes";
import { COULD_NOT_CHECK_IMPORT } from "@/stores/uploadTaskMonitorStore";

import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /**
     * Name of the item on the other Galaxy
     */
    name: string;
    /**
     * Status of the item's import in upload state
     */
    status: UploadStatus;
    /**
     * Why the import failed
     * @default undefined
     */
    error?: string;
}

const props = withDefaults(defineProps<Props>(), {
    error: undefined,
});
</script>

<template>
    <li class="galaxy-link-import-item mb-2" data-description="galaxy picker import item">
        <b>{{ props.name || "Unnamed item" }}</b>
        <span v-if="props.status === 'completed'" class="text-success">Imported</span>
        <span v-else-if="props.status === 'cancelled'" class="text-muted">Cancelled</span>
        <span
            v-else-if="props.status === 'error'"
            :class="props.error === COULD_NOT_CHECK_IMPORT ? 'text-warning' : 'text-danger'">
            {{ props.error }}
        </span>
        <LoadingSpan v-else message="Importing" />
    </li>
</template>
