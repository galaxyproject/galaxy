<script setup lang="ts">
import type { HDCASummary } from "@/api";

import CollectionDescription from "@/components/History/Content/Collection/CollectionDescription.vue";
import ContentExpirationIndicator from "@/components/History/Content/ContentExpirationIndicator.vue";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";

interface Props {
    dsc: HDCASummary;
    writeable: boolean;
    /** The annotation of the collection; only a collection that is a history item has one. */
    annotation?: string;
    showAnnotation?: boolean;
}

withDefaults(defineProps<Props>(), {
    annotation: undefined,
    showAnnotation: false,
});

const emit = defineEmits<{
    (e: "update:dsc", changes: Partial<HDCASummary>): void;
}>();
</script>

<template>
    <DetailsLayout
        :name="dsc.name ?? ''"
        :tags="dsc.tags"
        :writeable="writeable"
        :renameable="writeable"
        :annotation="annotation"
        :show-annotation="showAnnotation"
        @save="emit('update:dsc', $event)">
        <template v-slot:description>
            <CollectionDescription :hdca="dsc" />
            <ContentExpirationIndicator :item="dsc" />
        </template>
    </DetailsLayout>
</template>
