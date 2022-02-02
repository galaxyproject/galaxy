<template>
    <div class="history-listing">
        <div @scroll="onScrollThrottle" class="listing">
            <div v-for="(item, index) in getItems" :key="index">
                <HistoryContentItem
                    :item="item"
                    :expanded="isExpanded(item)"
                    :selected="isSelected(item)"
                    :show-selection="showSelection"
                    @update:expanded="setExpanded(item, $event)"
                    @update:selected="setSelected(item, $event)"
                    @viewCollection="$emit('viewCollection', item)" />
            </div>
            <div class="m-2">
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
        showSelection: { type: Boolean, required: true },
        isExpanded: { type: Function, required: true },
        isSelected: { type: Function, required: true },
        setExpanded: { type: Function, required: true },
        setSelected: { type: Function, required: true },
    },
    data() {
        return {
            items: [],
            maxNew: 10,
            throttlePeriod: 100,
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
        getItems() {
            return reverse(this.items.filter((n) => n));
        },
    },
    methods: {
        updateItems() {
            if (this.payload) {
                for (const item of this.payload) {
                    this.items[item.hid] = item;
                }
                this.items = this.items.slice();
            }
        },
        onScroll(event) {
            let topIndex = 0;
            for (const index in event.target.childNodes) {
                const child = event.target.childNodes[index];
                if (child.offsetTop > event.target.scrollTop) {
                    topIndex = index - 1;
                    break;
                }
            }
            topIndex = Math.min(Math.max(topIndex, 0), this.getItems.length - 1);
            this.$emit("scroll", this.getItems[topIndex].hid);
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
        z-index: 0;
    }
}
</style>
