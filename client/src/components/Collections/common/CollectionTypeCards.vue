<script setup lang="ts">
import { BCard, BCardText, BCardTitle } from "bootstrap-vue";
import { computed } from "vue";

import { borderVariant } from "@/components/Common/Wizard/utils";

import {
    type CollectionTypeContext,
    describeKnownCollectionType,
    findKnownCollectionTypes,
    KNOWN_COLLECTION_TYPE_GROUPS,
    type KnownCollectionType,
} from "./knownCollectionTypes";

const props = defineProps<{
    value?: string | null;
    context: CollectionTypeContext;
    /** Only these collection types, in this order and without group headings; every known type by default. */
    types?: string[];
    hideType?: boolean;
}>();

const emit = defineEmits<{
    (e: "select", collectionType: string): void;
}>();

const sections = computed<{ group?: string; types: KnownCollectionType[] }[]>(() =>
    props.types ? [{ types: findKnownCollectionTypes(props.types) }] : KNOWN_COLLECTION_TYPE_GROUPS,
);
</script>

<template>
    <div class="collection-type-cards" :class="{ 'collection-type-cards-grouped': !types }">
        <section v-for="{ group, types: sectionTypes } in sections" :key="group" class="collection-type-group">
            <h3 v-if="group" class="collection-type-group-title">{{ group }}</h3>
            <div class="collection-type-card-grid" :class="{ 'collection-type-card-grid-ungrouped': !group }">
                <BCard
                    v-for="known in sectionTypes"
                    :key="known.collectionType"
                    :data-collection-type="known.collectionType"
                    class="collection-type-card wizard-selection-card"
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
                    <code v-if="!hideType" class="collection-type-card-type"
                        ><span v-for="(part, index) in known.collectionType.split(':')" :key="index"
                            ><template v-if="index > 0">:<wbr /></template>{{ part }}</span
                        ></code
                    >
                    <BCardText class="collection-type-card-description">
                        {{ describeKnownCollectionType(known, context) }}
                    </BCardText>
                </BCard>
                <slot v-if="!group" name="extra" />
            </div>
        </section>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";

.collection-type-cards-grouped {
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

// a few cards share a row like a wizard's card deck; a flex row sizes to its cards, where a size container would
// collapse inside a wizard step that shrinks to fit its content
.collection-type-card-grid.collection-type-card-grid-ungrouped {
    display: flex;

    > * {
        flex: 1 1 0;
        min-width: 0;
    }

    @media (max-width: 575.98px) {
        flex-direction: column;
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
