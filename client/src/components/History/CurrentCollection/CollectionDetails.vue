<template>
    <Details
        :name="dsc.name"
        :tags="dsc.tags"
        :writeable="writeable"
        :show-annotation="false"
        @save="$emit('update:dsc', $event)">
        <template v-slot:name>
            <h3 v-short="dsc.name || 'Collection'" data-description="collection name display" />
            <CollectionDescription
                :job-state-summary="jobState"
                :collection-type="dsc.collection_type"
                :element-count="dsc.element_count"
                :elements-datatypes="dsc.elements_datatypes" />
        </template>
    </Details>
</template>

<script>
import short from "components/directives/v-short";
import Details from "components/History/Layout/Details";
import CollectionDescription from "components/History/Content/Collection/CollectionDescription";
import { JobStateSummary } from "components/History/Content/Collection/JobStateSummary";

export default {
    components: {
        CollectionDescription,
        Details,
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
