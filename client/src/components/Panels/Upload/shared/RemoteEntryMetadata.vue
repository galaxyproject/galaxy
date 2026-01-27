<script setup lang="ts">
import { faFingerprint } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

import type { RemoteEntry, RemoteFile } from "@/api/remoteFiles";
import { bytesToString } from "@/utils/utils";

import UtcDate from "@/components/UtcDate.vue";

interface Props {
    entry: RemoteEntry;
}

const props = defineProps<Props>();

const fileEntry = computed<RemoteFile | null>(() => {
    return props.entry.class === "File" ? props.entry : null;
});

const formattedSize = computed(() => {
    if (!fileEntry.value) {
        return null;
    }
    return bytesToString(fileEntry.value.size, true, 1);
});

const ctime = computed(() => {
    if (!fileEntry.value) {
        return null;
    }
    return fileEntry.value.ctime;
});

const hashTooltip = computed(() => {
    if (!fileEntry.value || !fileEntry.value.hashes || fileEntry.value.hashes.length === 0) {
        return "";
    }
    return fileEntry.value.hashes.map((h) => `${h.hash_function}: ${h.hash_value}`).join("\n");
});

const hasHashes = computed(() => !!fileEntry.value?.hashes && fileEntry.value.hashes.length > 0);
</script>

<template>
    <div class="remote-entry-metadata">
        <span v-if="formattedSize" class="metadata-item">{{ formattedSize }}</span>
        <span v-if="formattedSize && ctime" class="metadata-separator">•</span>
        <span v-if="ctime" class="metadata-item">
            <UtcDate :date="ctime" mode="pretty" />
        </span>
        <span v-if="hasHashes" v-b-tooltip.hover class="metadata-hash" :title="hashTooltip">
            <FontAwesomeIcon :icon="faFingerprint" />
        </span>
    </div>
</template>

<style scoped lang="scss">
.remote-entry-metadata {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;

    .metadata-item {
        white-space: nowrap;
    }

    .metadata-separator {
        opacity: 0.5;
        user-select: none;
    }

    .metadata-hash {
        margin-left: 0.25rem;
    }
}
</style>
