<script setup lang="ts">
import { BCard, BCardText, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import { KNOWN_COLLECTION_TYPE_GROUPS, KNOWN_COLLECTION_TYPES } from "./knownCollectionTypes";

defineProps<{
    value?: string | null;
}>();

const emit = defineEmits<{
    (e: "select", collectionType: string): void;
}>();

const groups = KNOWN_COLLECTION_TYPE_GROUPS.map((group) => ({
    group,
    types: KNOWN_COLLECTION_TYPES.filter((known) => known.group === group),
}));
</script>

<template>
    <div class="collection-type-cards">
        <section v-for="{ group, types } in groups" :key="group" class="mb-3">
            <h3 class="h-sm">{{ group }}</h3>
            <div class="collection-type-card-grid">
                <BCard
                    v-for="known in types"
                    :key="known.collectionType"
                    :data-collection-type="known.collectionType"
                    class="collection-type-card"
                    :border-variant="borderVariant(value === known.collectionType)"
                    role="button"
                    tabindex="0"
                    @click="emit('select', known.collectionType)"
                    @keydown.enter="emit('select', known.collectionType)"
                    @keydown.space.prevent="emit('select', known.collectionType)">
                    <BCardTitle title-tag="h4" class="h-sm">
                        <b>{{ known.label }}</b>
                    </BCardTitle>
                    <code>{{ known.collectionType }}</code>
                    <BCardText class="mt-2">{{ known.description }}</BCardText>
                </BCard>
            </div>
        </section>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.collection-type-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
    gap: 0.75rem;
}

.collection-type-card {
    border-width: 3px;

    &:hover,
    &:focus {
        border-color: lighten($brand-primary, 20%);
        cursor: pointer;
    }
}
</style>
