<template>
    <div>
        <ContentItem
            :item="item.object"
            :id="item.element_index"
            :name="item.element_identifier"
            :is-dataset="item.element_type == 'hda'"
            :expand-dataset="expandDataset"
            :is-history-item="false"
            @update:expand-dataset="expandDataset = $event"
            @view-collection="viewCollection = !viewCollection" />
        <GenericItem v-if="viewCollection" :itemId="item.object.id" :itemSrc="item.object.history_content_type" />
    </div>
</template>

<script>
import ContentItem from "./ContentItem";

export default {
    components: {
        ContentItem,
        GenericItem: () => import("components/History/Content/GenericItem"),
    },
    props: {
        item: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            viewCollection: false,
            expandDataset: false,
        };
    },
};
</script>
