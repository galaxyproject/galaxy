<template>
    <div class="history-listing">
        <virtual-list
            ref="listing"
            class="listing"
            :data-key="itemKey"
            :data-sources="getItems"
            :data-component="{}"
            @scroll="onScroll">
            <template v-slot:item="{ item }">
                <slot name="history-item" :item="item" />
            </template>
            <template v-slot:footer>
                <LoadingSpan v-if="loading" class="m-2" message="Loading" />
            </template>
        </virtual-list>
    </div>
</template>
<script>
import VirtualList from "vue-virtual-scroll-list";
import { reverse, throttle } from "lodash";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
        VirtualList,
    },
    props: {
        itemKey: { type: String, default: "hid" },
        limit: { type: Number, required: true },
        payload: { type: Array, default: null },
        queryKey: { type: String, default: null },
        reversed: { type: Boolean, default: false },
    },
    data() {
        return {
            items: [],
            throttlePeriod: 20,
            deltaMax: 20,
            queryCurrent: this.queryKey,
        };
    },
    created() {
        this.updateItems();
        this.onScrollThrottle = throttle((event) => {
            this.onScroll(event);
        }, this.throttlePeriod);
    },
    watch: {
        payload() {
            this.updateItems();
        },
    },
    computed: {
        loading() {
            return !!this.payload && this.payload.length == this.limit;
        },
        getItems() {
            const filtered = this.items.filter((n) => n);
            return this.reversed ? reverse(filtered) : filtered;
        },
    },
    methods: {
        updateItems() {
            /* This function merges the existing data with new incoming data. */
            if (this.queryKey != this.queryCurrent) {
                this.queryCurrent = this.queryKey;
                this.items = [];
            } else if (this.payload) {
                let hasNewItems = false;
                for (const item of this.payload) {
                    const itemIndex = item[this.itemKey];
                    if (this.items[itemIndex]) {
                        const localItem = this.items[itemIndex];
                        Object.keys(localItem).forEach((key) => {
                            localItem[key] = item[key];
                        });
                    } else {
                        hasNewItems = true;
                        this.items[itemIndex] = item;
                    }
                }
                if (hasNewItems) {
                    this.items = this.items.slice();
                }
            }
        },
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
.history-listing {
    .listing {
        @include absfill();
        scroll-behavior: smooth;
        overflow-y: scroll;
        overflow-x: hidden;
    }
}
</style>
