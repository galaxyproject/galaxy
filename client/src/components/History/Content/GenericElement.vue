<template>
    <div>
        <ContentItem
            :item="item"
            :id="item.element_index"
            :name="item.element_identifier"
            :expandable="item.element_type == 'hda'"
            :state="item.object.state"
            :expanded="expanded"
            :writeable="false"
            @update:expanded="expanded = $event"
            @drilldown="drilldown = !drilldown" />
        <GenericItem v-if="drilldown" :itemId="item.object.id" :itemSrc="item.object.history_content_type" />
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
            drilldown: false,
            expanded: false,
        };
    },
};
</script>
