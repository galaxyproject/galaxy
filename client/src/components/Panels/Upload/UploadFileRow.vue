<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { UploadItem } from "@/composables/upload/uploadItemTypes";
import { bytesToString } from "@/utils/utils";

import { getFileProgressUi } from "./uploadProgressUi";

interface Props {
    file: UploadItem;
    nested?: boolean;
}

const props = defineProps<Props>();

const ui = computed(() => getFileProgressUi(props.file));
</script>

<template>
    <div class="file-detail-item" :class="[{ nested: props.nested, 'has-error': props.file.status === 'error' }]">
        <div class="d-flex align-items-center mb-1">
            <FontAwesomeIcon :icon="ui.icon" :class="ui.textClass" :spin="ui.spin" class="mr-2" fixed-width size="sm" />
            <span class="file-name flex-grow-1" :title="props.file.name">{{ props.file.name }}</span>
            <span class="text-muted small ml-2">{{ bytesToString(props.file.size) }}</span>
            <span class="text-muted small ml-2">{{ props.file.progress }}%</span>
        </div>
        <div class="progress" style="height: 3px">
            <div
                class="progress-bar"
                :class="ui.barClass"
                :style="{ width: `${props.file.progress}%` }"
                role="progressbar"
                :aria-valuenow="props.file.progress"
                aria-valuemin="0"
                aria-valuemax="100"></div>
        </div>
        <div v-if="props.file.error" class="error-message text-danger small mt-1">
            {{ props.file.error }}
        </div>
    </div>
</template>
