<template>
    <Details
        :name="name"
        :tags="dsc.tags"
        :writeable="writeable"
        :show-annotation="false"
        @save="$emit('update:dsc', $event)">
        <template v-slot:name>
            <h3 data-description="collection name display">{{ name || "Collection" }}</h3>
            <ContentDescription :item="dsc" />
        </template>
    </Details>
</template>

<script>
import Details from "components/History/Layout/Details";
import ContentDescription from "components/History/Content/ContentDescription";

export default {
    components: {
        ContentDescription,
        Details,
    },
    props: {
        dsc: { type: Object, required: true },
        writeable: { type: Boolean, required: true },
    },
    computed: {
        name() {
            return this.dsc.name || this.dsc.element_identifier;
        },
    },
};
</script>
