<template>
    <div class="history-listing">
        <div @scroll="onScrollThrottle" class="listing">
            <div v-for="(item, index) in getItems" :key="index">
                <slot name="history-item" :item="item" :index="index" />
            </div>
            <div v-if="loading" class="m-2">
                <LoadingSpan message="Please wait" />
            </div>
        </div>
    </div>
</template>
<script>
import { reverse, throttle } from "lodash";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
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
            throttlePeriod: 100,
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
                    this.$emit("scroll", topItem[this.itemKey]);
                }
            }
        },
    },
};
</script>

<style scoped lang="scss">
@import "scss/mixins.scss";
.history-listing {
    .listing {
        @include absfill();
        overflow-y: scroll;
        overflow-x: hidden;
    }
}
</style>
