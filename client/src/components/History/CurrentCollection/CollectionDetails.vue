<template>
    <Details
        :name="dsc.name"
        :tags="dsc.tags"
        :writeable="writeable"
        :show-annotation="false"
        @save="$emit('update:dsc', $event)">
        <template v-slot:name>
            <h3 data-description="collection name display">{{ dsc.name || "Collection" }}</h3>
            <CollectionDescription :item="dsc" />
        </template>
    </Details>
</template>

<script>
import Details from "components/History/Layout/Details";
import CollectionDescription from "components/History/Content/Collection/CollectionDescription";

export default {
    components: {
        CollectionDescription,
        Details,
    },
    props: {
        dsc: { type: Object, required: true },
        writeable: { type: Boolean, required: true },
    },
};
</script>
