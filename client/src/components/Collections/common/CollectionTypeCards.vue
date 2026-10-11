<script setup lang="ts">
import { BCard, BCardText, BCardTitle } from "bootstrap-vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import { KNOWN_COLLECTION_TYPE_GROUPS } from "./knownCollectionTypes";

defineProps<{
    value?: string | null;
}>();

const emit = defineEmits<{
    (e: "select", collectionType: string): void;
}>();
</script>

<template>
    <div class="collection-type-cards">
        <section v-for="{ group, types } in KNOWN_COLLECTION_TYPE_GROUPS" :key="group" class="collection-type-group">
            <h3 class="collection-type-group-title">{{ group }}</h3>
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
                    <BCardTitle title-tag="h4" class="h-sm mb-1">
                        <b>{{ known.label }}</b>
                    </BCardTitle>
                    <!-- break long types like sample_sheet:paired_or_unpaired after a colon, not mid-word -->
                    <code class="collection-type-card-type"
                        ><span v-for="(part, index) in known.collectionType.split(':')" :key="index"
                            ><template v-if="index > 0">:<wbr /></template>{{ part }}</span
                        ></code
                    >
                    <BCardText class="collection-type-card-description">{{ known.description }}</BCardText>
                </BCard>
            </div>
        </section>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.collection-type-cards {
    container-type: inline-size;
}

.collection-type-group + .collection-type-group {
    margin-top: var(--spacing-6);
}

.collection-type-group-title {
    font-size: var(--font-size-small);
    font-weight: bold;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--color-grey-500);
    border-bottom: 1px solid $border-color;
    padding-bottom: var(--spacing-1);
    margin-bottom: var(--spacing-3);
}

// The same number of columns in every group, so cards line up from one group to the next and a row spans the width.
.collection-type-card-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: var(--spacing-3);
}

@container (min-width: 32rem) {
    .collection-type-card-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@container (min-width: 60rem) {
    .collection-type-card-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }
}

.collection-type-card {
    border-width: 3px;

    &:hover,
    &:focus {
        border-color: lighten($brand-primary, 20%);
        cursor: pointer;
    }
}

.collection-type-card-type {
    display: block;
    font-size: var(--font-size-small);
}

.collection-type-card-description {
    margin-top: var(--spacing-3);
}
</style>
