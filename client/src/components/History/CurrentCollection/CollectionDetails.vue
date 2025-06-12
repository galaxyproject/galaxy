<script setup lang="ts">
import type { HDCASummary } from "@/api";

import CollectionDescription from "@/components/History/Content/Collection/CollectionDescription.vue";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";

interface Props {
    dsc: HDCASummary;
    writeable: boolean;
}

defineProps<Props>();
</script>

<template>
    <DetailsLayout
        :name="dsc.name ?? ''"
        :tags="dsc.tags"
        :writeable="writeable"
        :show-annotation="false"
        @save="$emit('update:dsc', $event)">
        <template v-slot:description>
            <CollectionDescription :hdca="dsc" />
        </template>
    </DetailsLayout>
</template>
