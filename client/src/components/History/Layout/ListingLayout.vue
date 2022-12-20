<template>
    <div class="listing-layout">
        <virtual-list
            ref="listing"
            class="listing"
            role="list"
            data-key="id"
            :offset="offset"
            :data-sources="items"
            :data-component="{}"
            @scroll="onScroll">
            <template v-slot:item="{ item }">
                <slot name="item" :item="item" :current-offset="getOffset()" />
            </template>
            <template v-slot:footer>
                <LoadingSpan v-if="loading" class="m-2" message="Loading" />
            </template>
        </virtual-list>
    </div>
</template>
<script>
import VirtualList from "vue-virtual-scroll-list";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
        VirtualList,
    },
    props: {
        offset: { type: Number, default: 0 },
        loading: { type: Boolean, default: false },
        items: { type: Array, default: null },
        queryKey: { type: String, default: null },
    },
    data() {
        return {
            previousStart: undefined,
        };
    },
    watch: {
        queryKey() {
            this.$refs.listing.scrollToOffset(0);
        },
    },
    methods: {
        onScroll() {
            const rangeStart = this.$refs.listing.range.start;
            if (this.previousStart !== rangeStart) {
                this.previousStart = rangeStart;
                this.$emit("scroll", rangeStart);
            }
        },
        getOffset() {
            return this.$refs.listing?.getOffset() || 0;
        },
    },
};
</script>

<style scoped lang="scss">
@import "scss/mixins.scss";
.listing-layout {
    .listing {
        @include absfill();
        scroll-behavior: smooth;
        overflow-y: scroll;
        overflow-x: hidden;
    }
}
</style>
