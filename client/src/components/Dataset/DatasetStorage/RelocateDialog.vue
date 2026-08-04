<script setup lang="ts">
import type { UserConcreteObjectStoreModel } from "@/api";

import Heading from "@/components/Common/Heading.vue";
import SourceOptionCard from "@/components/ConfigTemplates/SourceOptionCard.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

interface RelocateProps {
    fromObjectStore: UserConcreteObjectStoreModel;
    targetObjectStores: UserConcreteObjectStoreModel[];
}

defineProps<RelocateProps>();

const emit = defineEmits<{
    (e: "relocate", value: string): void;
}>();

function relocate(objectStoreId?: string | null) {
    if (objectStoreId) {
        emit("relocate", objectStoreId);
    }
}
</script>

<template>
    <div>
        <Heading size="sm" separator>Currently the dataset is located in</Heading>
        <div class="select-card-group">
            <SourceOptionCard :source-option="fromObjectStore" selected>
                <template v-slot:badges>
                    <ObjectStoreBadges :badges="fromObjectStore.badges" size="lg" />
                </template>
            </SourceOptionCard>
        </div>
        <Heading size="sm" separator>Select new Galaxy storage for the dataset</Heading>
        <div class="select-card-group">
            <SourceOptionCard
                v-for="objectStore in targetObjectStores"
                :key="objectStore.object_store_id"
                :source-option="objectStore"
                submit-button-tooltip="Relocate the dataset to this storage location"
                @select="relocate(objectStore.object_store_id)">
                <template v-slot:badges>
                    <ObjectStoreBadges :badges="objectStore.badges" size="lg" />
                </template>
            </SourceOptionCard>
        </div>
    </div>
</template>

<style scoped>
.select-card-group {
    display: flex;
    flex-wrap: wrap;
    margin: auto;
}
</style>
