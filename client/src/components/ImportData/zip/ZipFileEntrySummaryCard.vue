<script setup lang="ts">
import type { ImportableFile } from "@/composables/zipExplorer";

import GCard from "@/components/Common/GCard.vue";

interface Props {
    file: ImportableFile;
}

defineProps<Props>();
</script>

<template>
    <GCard :id="file.path" :title="file.name" class="zip-file-summary-card">
        <template v-slot:description>
            <div v-if="file.path !== file.name" class="zip-file-path text-muted">
                {{ file.path }}
            </div>
            <div v-if="file.description">{{ file.description }}</div>
        </template>
    </GCard>
</template>
