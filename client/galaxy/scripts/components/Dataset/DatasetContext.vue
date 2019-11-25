<template>
    <div>
        <b-button
            v-b-tooltip.hover.bottom
            title="Add to current History"
            class="dataset-add btn-sm btn-primary fa fa-plus"
            @click="addToHistory"
        />
    </div>
</template>
<script>
export default {
    props: {
        item: Object
    },
    methods: {
        addToHistory() {
            this.$emit("addToHistory", this.item);
        }
    }
};
</script>
