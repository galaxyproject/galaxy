<script setup lang="ts">
import type { ImportableFile } from "@/composables/zipExplorer";
import { bytesToString } from "@/utils/utils";

import UtcDate from "@/components/UtcDate.vue";

defineProps<{
    file: ImportableFile;
}>();
</script>

<template>
    <!-- TODO: Replace with GCard -->
    <div class="zip-file-entry-card">
        <span>{{ file.path }}</span>
        <br />
        <strong>{{ file.name }}</strong>
        <span>({{ bytesToString(file.size, true, undefined) }})</span>
        <UtcDate :date="file.dateTime.toISOString()" mode="elapsed" />
        <span v-if="file.description">
            <br />
            {{ file.description }}
        </span>
    </div>
</template>

<style scoped lang="scss">
.zip-file-entry-card {
    padding: 1rem;
    border: 1px solid #000000;
    border-radius: 0.2rem;
    background-color: #f9f9f9;
}
</style>
