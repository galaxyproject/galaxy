<script setup lang="ts">
import type { UserConcreteObjectStoreModel } from "@/api";

import SourceOptionCard from "@/components/ConfigTemplates/SourceOptionCard.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

interface RelocateProps {
    objectStores: UserConcreteObjectStoreModel[];
}

defineProps<RelocateProps>();

const emit = defineEmits<{
    (e: "select", value: string | null): void;
}>();
</script>

<template>
    <div>
        <SourceOptionCard
            v-for="objectStore in objectStores"
            :key="objectStore.object_store_id"
            :source-option="objectStore"
            submit-button-tooltip="Filter datasets to this storage location"
            @select="emit('select', objectStore.object_store_id ?? null)">
            <template v-slot:badges>
                <ObjectStoreBadges :badges="objectStore.badges" size="lg" />
            </template>
        </SourceOptionCard>
    </div>
</template>
