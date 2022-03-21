<template>
    <h6 v-if="collectionType" class="description py-1">
        <span>a {{ collectionLabel | localize }}</span>
        <span v-if="elementCount == 1">with 1 item</span>
        <span v-else-if="elementCount > 1">with {{ elementCount }} items</span>
    </h6>
</template>

<script>
export default {
    props: {
        item: { type: Object, required: true },
    },
    data() {
        return {
            labels: {
                list: "list",
                paired: "dataset pair",
                "list:paired": "list of pairs",
            },
        };
    },
    computed: {
        collectionLabel() {
            return this.labels[this.collectionType] || "nested list";
        },
        collectionType() {
            return this.item.collection_type;
        },
        elementCount() {
            return this.item.element_count;
        },
    },
};
</script>
