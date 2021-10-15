<template>
    <div ref="container" class="scrollContainer">
        <div
            v-infinite-scroll="getMoreContent"
            infinite-scroll-disabled="busy"
            infinite-scroll-distance="0"
            @scroll="debouncedScroll"
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
import { reverse, debounce } from "lodash";
import { HistoryContentItem } from "./ContentItem";
import infiniteScroll from "vue-infinite-scroll";
import { setTimeout } from "timers";
import axios from "axios";

export default {
    directives: { infiniteScroll },
    components: {
        HistoryContentItem,
    },
    created() {
        this.pollAboveMaxHid();
        // axios call to get max_hid TODO - should this be somewhere else? where?
        axios.get(`/api/histories/${this.historyId}/contents/before/1/1`).then((data) => {
            //this came back as a String, oddly, so I needed to coerce it to a Number
            this.maxHid = data.headers.max_hid > 0 ? Number(data.headers.max_hid) : 0;
        });
        this.debouncedScroll = debounce((event) => this.handleScroll(event), 100);
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
            return this.data.length > 0 ? this.data : this.payload.contents;
        },
        startKey() {
            return this.payload.startKey;
        },
    },
    watch: {
        historyId: function () {
            this.changeHistory();
        },
        payload: function () {
            if (this.payload?.contents.length > 0) {
                this.payload.contents.forEach((element) => {
                    Vue.set(this.data, element.hid, element);
                });
            }
        },
        resetHistoryContents: function(newVal, oldVal) {
            if (newVal) {
                this.data = [];
                this.setScrollPos({ key: this.maxHid })
                this.setResetHistoryContents(false);
            }
        }
    },
    props: {
        setScrollPos: { type: Function, required: true },
        payload: { required: true },
        showSelection: { type: Boolean, required: true },
        isExpanded: { type: Function, required: true },
        setExpanded: { type: Function, required: true },
        isSelected: { type: Function, required: true },
        setSelected: { type: Function, required: true },
        loading: { type: Boolean, required: true },
        historyId: { type: String, required: true },
        resetHistoryContents: {required: true},
        setResetHistoryContents: {required: true}
    },
    methods: {
        handleScroll(event) {
            const percent = event.target.scrollTop / event.target.scrollHeight;
            const index = Math.floor(percent * this.getDisplayData.length);
            this.setScrollPos({ key: this.getDisplayData[index].hid });
        },
        changeHistory() {
            this.data = [];
            this.initialLoad = true;
            this.maxHid = 0;
        },
        pollAboveMaxHid() {
            this.maxHidPoll = setInterval(() => {
                if (this.maxHid > 0 || this.getSortedData.length == 0) {
                    axios.get(`/api/histories/${this.historyId}/contents/near/${this.maxHid}/60`).then((response) => {
                        //this came back as a String, oddly, so I needed to coerce it to a Number
                        const newMaxHid = response.headers.max_hid > 0 ? Number(response.headers.max_hid) : this.maxHid;
                        if (newMaxHid !== this.maxHid) {
                            this.maxHid = newMaxHid;
                            response.data.forEach((element) => {
                                Vue.set(this.data, element.hid, element);
                            });
                        }
                    });
                }
            }, 3000);
        },
        removeItem(event) {
            this.data[event].isDeleted = true;
        },
        getMoreContent() {
            this.busy = true;
            setTimeout(() => {
                if (this.initialLoad) {
                    // Get all history items before, including the one at maxHid
                    this.setScrollPos({ key: this.maxHid });
                    this.initialLoad = false;
                } else if (this.getSortedData.length > 0) {
                    this.setScrollPos({ key: this.getSortedData[this.getSortedData.length - 1].hid });
                }
                this.busy = false;
            }, 2000);
        },
    },
    beforeDestroy() {
        clearInterval(this.maxHidPoll);
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
