<script setup lang="ts">
import { type ObjectStoreBadgeType } from "@/api/objectStores.templates";

import ObjectStoreBadge from "@/components/ObjectStore/ObjectStoreBadge.vue";

interface Props {
    badges: ObjectStoreBadgeType[];
    size?: string;
}

defineProps<Props>();
</script>

<template>
    <div class="object-store-badges">
        <ObjectStoreBadge v-for="(badge, idx) in badges" :key="idx" :badge="badge" :size="size" />
    </div>
</template>

<style scoped>
.object-store-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem;
    justify-content: right;
}
</style>
