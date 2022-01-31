<template>
    <div ref="container" class="scrollContainer">
        <div
            infinite-scroll-disabled="busy"
            @scroll="handleScroll"
            :class="{ loadingBackground: loading, listing: true }">
            <div v-for="(item, index, rowKey) in getDisplayData" :key="rowKey">
                <HistoryContentItem
                    :item="item"
                    :index="index"
                    :row-key="rowKey"
                    :show-selection="showSelection"
                    :expanded="isExpanded(item)"
                    @update:expanded="setExpanded(item, $event)"
                    :selected="isSelected(item)"
                    @update:selected="setSelected(item, $event)"
                    @viewCollection="$emit('viewCollection', item)"
                    @deleted="removeItem"
                    :data-hid="item.hid"
                    :data-index="index"
                    :data-row-key="rowKey" />
            </div>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import { reverse } from "lodash";
import { HistoryContentItem } from "./ContentItem";

export default {
    components: {
        HistoryContentItem,
    },
    data() {
        return {
            maxHidPoll: null,
            initialLoad: true,
            data: [],
            maxHid: 0,
            debouncedScroll: () => {},
        };
    },
    computed: {
        getDisplayData() {
            return this.getSortedData.filter((item) => item.visible && !item.isDeleted);
        },
        getSortedData() {
            // Indexing the history items by their HID creates a sparse
            // array (in the case where there is a gap between HIDs).
            // Filter out nulls and sort the array in descending order
            // for display
            return reverse(this.getData.filter((n) => n));
        },
        getData() {
            return this.data.length > 0 ? this.data : this.payload;
        },
    },
    watch: {
        historyId: function () {
            this.changeHistory();
        },
        payload: function () {
            if (this.payload?.length > 0) {
                this.payload.forEach((element) => {
                    Vue.set(this.data, element.hid, element);
                });
            }
        },
        resetHistoryContents: function (newVal, oldVal) {
            /*if (newVal) {
                this.data = [];
                this.setScrollPos({ key: this.maxHid });
                this.setResetHistoryContents(false);
            }*/
        },
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
        resetHistoryContents: { required: true },
        setResetHistoryContents: { required: true },
    },
    methods: {
        handleScroll(event) {
            const percent = event.target.scrollTop / event.target.scrollHeight;
            const index = Math.floor(percent * this.getDisplayData.length);
            this.$emit("scroll", this.getDisplayData[index].hid);
        },
        changeHistory() {
            this.data = [];
            this.initialLoad = true;
            this.maxHid = 0;
        },
        removeItem(event) {
            this.data[event].isDeleted = true;
        },
    },
};
</script>

<style lang="scss">
@import "scss/mixins.scss";
.scrollContainer {
    .listing {
        overflow-y: scroll;
        z-index: 0;
    }
}
</style>
