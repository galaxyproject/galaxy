<template>
    <div class="history-listing">
        <div @scroll="onScroll" class="listing">
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
        </div>
    </div>
</template>
<script>
import { reverse } from "lodash";
import { HistoryContentItem } from "./ContentItem";

export default {
    components: {
        HistoryContentItem,
    },
    props: {
        payload: { required: true },
        showSelection: { type: Boolean, required: true },
        isExpanded: { type: Function, required: true },
        setExpanded: { type: Function, required: true },
        isSelected: { type: Function, required: true },
        setSelected: { type: Function, required: true },
        loading: { type: Boolean, required: true },
        historyId: { type: String, required: true },
    },
    data() {
        return {
            items: [],
            maxNew: 10,
        };
    },
    created() {
        this.updateItems();
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
            const percent = event.target.scrollTop / event.target.scrollHeight;
            const index = Math.max(Math.min(Math.floor(percent * this.getItems.length), 0), this.getItems.length - 1);
            this.$emit("scroll", this.getItems[index].hid + this.maxNew);
        },
    },
};
</script>

<style scoped lang="scss">
@import "scss/mixins.scss";
.history-listing {
    .listing {
        overflow-y: scroll;
        z-index: 0;
    }
}
</style>
