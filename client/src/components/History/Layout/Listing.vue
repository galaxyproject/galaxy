<template>
    <div class="listing-layout">
        <virtual-list
            ref="listing"
            class="listing"
            data-key="id"
            :data-sources="items"
            :data-component="{}"
            @scroll="onScroll">
            <template v-slot:item="{ item }">
                <slot name="item" :item="item" />
            </template>
            <template v-slot:footer>
                <LoadingSpan v-if="loading" class="m-2" message="Loading" />
            </template>
        </virtual-list>
    </div>
</template>
<script>
import VirtualList from "vue-virtual-scroll-list";
import { throttle } from "lodash";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
        VirtualList,
    },
    props: {
        loading: { type: Boolean, default: false },
        items: { type: Array, default: null },
        queryKey: { type: String, default: null },
    },
    data() {
        return {
            throttlePeriod: 20,
            deltaMax: 20,
        };
    },
    watch: {
        queryKey() {
            this.$refs.listing.scrollToOffset(0);
        },
    },
    created() {
        this.onScrollThrottle = throttle((event) => {
            this.onScroll(event);
        }, this.throttlePeriod);
    },
    methods: {
        onScrollHandler(event) {
            /* CURRENTLY UNUSED
            // this avoids diagonal scrolling, we either scroll left/right or top/down
            // both events are throttled and the default handler has been prevented.
            if (Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
                // handle vertical scrolling with virtual scroller
                const listing = this.$refs.listing;
                const deltaMax = this.deltaMax;
                const deltaY = Math.max(Math.min(event.deltaY, deltaMax), -deltaMax);
                this.offset = Math.max(0, listing.getOffset() + deltaY);
                this.$refs.listing.scrollToOffset(this.offset);
            } else {
                // dispatch horizontal scrolling as regular event
                var wheelEvent = new WheelEvent("wheel", {
                    deltaX: event.deltaX,
                    bubbles: true,
                    cancelable: false,
                });
                event.target.dispatchEvent(wheelEvent);
            }
            */
        },
        onScroll() {
            const rangeStart = this.$refs.listing.range.start;
            this.$emit("scroll", rangeStart);
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
