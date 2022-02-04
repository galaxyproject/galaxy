<template>
    <div class="history-listing">
        <div @scroll="onScrollThrottle" class="listing">
            <div v-for="(item, index) in getItems" :key="index">
                <HistoryContentItem
                    v-if="!hiddenItems[item.hid]"
                    :item="item"
                    :expanded="isExpanded(item)"
                    :selected="isSelected(item)"
                    :show-selection="showSelection"
                    @update:expanded="setExpanded(item, $event)"
                    @update:selected="setSelected(item, $event)"
                    @viewCollection="$emit('viewCollection', item)" />
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
import { HistoryContentItem } from "./ContentItem";

export default {
    components: {
        LoadingSpan,
        HistoryContentItem,
    },
    props: {
        payload: { required: true },
        hiddenItems: { type: Object, required: true },
        queryKey: { type: String, default: null },
        pageSize: { type: Number, required: true },
        showSelection: { type: Boolean, required: true },
        isExpanded: { type: Function, required: true },
        isSelected: { type: Function, required: true },
        setExpanded: { type: Function, required: true },
        setSelected: { type: Function, required: true },
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
            return this.payload.length == this.pageSize;
        },
        hasItems() {
            return this.items.length > 0;
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
                    const isHidden = this.hiddenItems[item.hid];
                    this.items[item.hid] = isHidden ? null : item;
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
                    this.$emit("scroll", topItem.hid);
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
        overflow-y: scroll;
        overflow-x: hidden;
    }
}
</style>
