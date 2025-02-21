<script setup lang="ts">
import { computed } from "vue";

import { type HDCASummary } from "@/api";
import { JobStateSummary } from "@/components/History/Content/Collection/JobStateSummary.js";

import CollectionDescription from "@/components/History/Content/Collection/CollectionDescription.vue";
import DetailsLayout from "@/components/History/Layout/DetailsLayout.vue";

interface Props {
    dsc: HDCASummary;
    writeable: boolean;
}

const props = defineProps<Props>();

const jobState = computed(() => {
    return new JobStateSummary(props.dsc);
});
</script>

<template>
    <DetailsLayout
        :name="dsc.name ?? ''"
        :tags="dsc.tags"
        :writeable="writeable"
        :show-annotation="false"
        @save="$emit('update:dsc', $event)">
        <template v-slot:name>
            <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
            <h2 v-short="dsc.name || 'Collection'" class="h-md" data-description="collection name display" />

            <CollectionDescription
                :job-state-summary="jobState"
                :collection-type="dsc.collection_type"
                :element-count="dsc.element_count ?? undefined"
                :elements-datatypes="dsc.elements_datatypes" />
        </template>
    </DetailsLayout>
</template>
