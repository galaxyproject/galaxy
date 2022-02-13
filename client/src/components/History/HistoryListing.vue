<template>
    <div
        class="history-listing"
        @scroll.prevent="onScrollThrottle"
        @wheel.prevent="onScrollThrottle"
        @touchmove.prevent="onScrollThrottle"
    >
        <virtual-list ref="listing" class="listing" data-key="hid" :data-sources="getItems" :data-component="{}">
            <template v-slot:item="{ item }">
                <slot name="history-item" :item="item" />
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
        payload: { required: true },
        itemKey: { type: String, default: "hid" },
        queryKey: { type: String, default: null },
        pageSize: { type: Number, required: true },
    },
    data() {
        return {
            items: [],
            throttlePeriod: 10,
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
            return !!this.payload && this.payload.length == this.pageSize;
        },
        getItems() {
            return reverse(this.items.filter((n) => n));
        },
    },
    methods: {
        updateItems() {
            if (this.queryKey != this.queryCurrent) {
                this.queryCurrent = this.queryKey;
                this.items = [];
            } else if (this.payload) {
                for (const item of this.payload) {
                    const itemIndex = item[this.itemKey];
                    this.items[itemIndex] = item;
                }
                this.items = this.items.slice();
            }
        },
        onScroll(event) {
            const listing = this.$refs["listing"];
            const deltaMax = this.deltaMax;
            const deltaY = Math.max(Math.min(event.deltaY, deltaMax), -deltaMax);
            this.offset = Math.max(0, listing.getOffset() + deltaY);
            listing.scrollToOffset(this.offset);
        },
        /*onScroll(event) {
            const itemCount = this.items.length;
            if (itemCount > 0) {
                let topIndex = 0;
                for (const index in event.target.childNodes) {
                    const child = event.target.childNodes[index];
                    if (child.offsetTop > event.target.scrollTop) {
                        topIndex = index - 1;
                        break;
                    }
                }
                topIndex = Math.min(Math.max(topIndex, 0), itemCount - 1);
                const topItem = this.getItems[topIndex];
                if (topItem) {
                    this.$emit("scroll", topIndex);
                }
            }
        },*/
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
