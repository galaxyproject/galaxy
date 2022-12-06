<template>
    <DetailsLayout
        :name="dsc.name"
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
                :element-count="dsc.element_count"
                :elements-datatypes="dsc.elements_datatypes" />
        </template>
    </DetailsLayout>
</template>

<script>
import short from "components/directives/v-short";
import DetailsLayout from "components/History/Layout/DetailsLayout";
import CollectionDescription from "components/History/Content/Collection/CollectionDescription";
import { JobStateSummary } from "components/History/Content/Collection/JobStateSummary";

export default {
    components: {
        CollectionDescription,
        DetailsLayout,
    },
    directives: {
        short,
    },
    props: {
        dsc: { type: Object, required: true },
        writeable: { type: Boolean, required: true },
    },
    computed: {
        jobState() {
            return new JobStateSummary(this.dsc);
        },
    },
};
</script>
