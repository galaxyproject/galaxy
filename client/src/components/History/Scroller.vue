<template>
    <div ref="container" class="scrollContainer" @wheel.prevent="onWheel">
        <!-- mousewheel moves up and down linearly, allows for fine-tuning of view by moving just a
        few rows at a time -->
        <div ref="listing" class="listing">
            <ul>
                <li v-for="(item, index) in itemWindow" :key="getItemKey(item, index)">
                    <slot :item="item" :index="index" :row-key="getItemKey(item, index)">
                        <pre>{{ item }}</pre>
                    </slot>
                </li>
            </ul>
        </div>

        <!-- big blank scroll region uses scroll bar to drag view to entirely new region, calculated
        by visual height of the scroller knob --->
        <div
            v-show="showScroller"
            ref="scrollSliderContainer"
            class="scrollSliderContainer"
            :style="scrollSliderContainerStyles"
            @scroll="onScroll"
        >
            <div ref="scrollSlider"></div>
        </div>
    </div>
</template>

<script>
import { debounce } from "lodash";
import { SearchParams } from "./model";

const clean = (o) => JSON.parse(JSON.stringify(o));

export default {
    props: {
        // field in the item data that represents the "primary" key, less for caching purposes than
        // Vue re-rendering comparison purposes. Should be a unique value from the list of data, and
        // is typically HID for history contents and element_index for collection contents
        keyField: { type: String, required: true },

        // A list of items to render in the immediate region of the scroll pos
        contents: { type: Array, required: true },

        // index from contents to start rendering, will be 0 for top of list,
        // we provide more contents than are currently rendered so the user can quickly
        // scroll outside the immediate window and still have a little data
        startKeyIndex: { type: Number, default: 0 },

        // known total matches for this list of content independent of pagination or
        // view windowing concerns, the raw data row count
        totalMatches: { type: Number, default: 0 },

        // number of undelivered rows above contents
        topRows: { type: Number, default: 0 },
        bottomRows: { type: Number, default: 0 },

        // Number of items from contents to render starting from the startKeyIndex
        pageSize: { type: Number, default: SearchParams.pageSize },

        // avoid an infinite loop when we visually adjust the scroller bar upon
        // receiving new content by suppressing outgoing update events until the
        // DOM update has finished.
        suppressionPeriod: { type: Number, default: 250 },

        // debug flag
        debug: { type: Boolean, default: false },
    },

    data() {
        return {
            // manual change of start key index, happens when user moves mouse-wheel
            manualStartIndex: null,

            // width of scroll bar container
            sbWidth: 30,
        };
    },

    computed: {
        // The index to start rendering content at, can be manually adjusted with
        // the mouse wheel, and must be updated when new contents come in
        itemStartIndex() {
            return this.manualStartIndex ?? this.startKeyIndex;
        },

        // The slice of contents to render right now, this is the actual data we loop over in the template
        itemWindow() {
            return this.contents.slice(this.itemStartIndex, this.itemStartIndex + this.pageSize);
        },

        // starting row index if we include the undelivered topRows, this is a
        // number representing how far down we are in the complete data set
        dataStartIndex() {
            return this.itemStartIndex + this.topRows;
        },

        // The portion of the way down the total list as descrbed by the input props
        cursor() {
            return this.totalMatches > 0 ? this.dataStartIndex / this.totalMatches : 0;
        },

        // user switched key, this is the row that was switched to
        manualStartKey() {
            const newIdx = this.manualStartIndex;
            return this.contents?.[newIdx]?.[this.keyField];
        },

        // need to dynamically calculate width
        scrollSliderContainerStyles() {
            const w = this.sbWidth;
            return { width: `${w}px` };
        },

        // show/hide the draggable scrollbar
        showScroller() {
            return this.sbWidth > 0 || this.topRows > 0;
        },
    },

    watch: {
        // when contents are updated, reset manualStartIndex
        // to pay attention to the passed in startKeyIndex instead
        // of the manual value we set when the user moved the mouse wheel
        contents() {
            this.manualStartIndex = null;
        },

        // When user moves the mouse wheel request more data by row key, since
        // we should have that value
        manualStartKey(key, oldKey) {
            if (key !== undefined && key !== oldKey) {
                this.$emit("scroll", { key });
            }
        },

        cursor(newVal) {
            this.debouncedAdjustScrollTop(newVal);
        },
    },

    created() {
        // non-reactive data
        this.suppressEvents = false;
        this.suppressionTimeout = null;
        this.debouncedUpdateCursor = debounce(this.updateCursor, 100);
        this.debouncedAdjustScrollTop = debounce(this.adjustScrollTop, 100);
    },

    updated() {
        this.checkScrollbars();
        // this.reportProps("updated");
    },

    mounted() {
        this.checkScrollbars();
    },

    methods: {
        log(...args) {
            if (this.debug) {
                console.log("Scroller ->", ...args);
            }
        },

        reportProps(label) {
            const data = clean(this._data);
            const props = clean(this._props);
            console.group(label);
            console.dir({ data, props });
            console.groupEnd();
        },

        getItemKey(item) {
            return item[this.keyField];
        },

        // move the list up and down with the mouse wheel incrementally
        // shifts manual startIndex up and down

        onWheel({ deltaY }) {
            // no wheel if list too short to warrant a scroll bar
            // let the browser figure that out
            if (this.showScroller) {
                if (deltaY > 0) this.wheelDown();
                if (deltaY < 0) this.wheelUp();
            }
        },

        wheelDown(n = 1) {
            this.manualStartIndex = Math.min(this.itemStartIndex + n, this.totalMatches - 1);
        },

        wheelUp(n = 1) {
            this.manualStartIndex = Math.max(0, this.itemStartIndex - n);
        },

        // move to whole new regions with the scrollbar, takes the percentage
        // of the height of the fake placeholder box and turns that into a 0-1
        // value which we send out on scrollPos

        onScroll() {
            this.debouncedUpdateCursor();
        },

        // determines cursor from scrollTop, need to wait until after render to calculate
        // this stuff because it depends on DOM elements
        updateCursor() {
            if (this.suppressEvents) return;

            const box = this.$refs.scrollSliderContainer;
            const slider = this.$refs.scrollSlider;

            this.log("updateCursor", slider.clientHeight, box.clientHeight, box.scrollTop);

            const maxHeight = Math.abs(slider.clientHeight - box.clientHeight);
            const cursor = maxHeight > 0 ? box.scrollTop / maxHeight : 0;
            this.$emit("scroll", { cursor });
        },

        // adjust scrolltop from scrollPos prop, happens on a content load
        // when the content window changes, may need to adjust the position
        // of the scroll bar handle, but we don't want to retrigger a bunch
        // of extraneous scroll events in the process.

        adjustScrollTop(newCursor) {
            const box = this.$refs.scrollSliderContainer;
            const slider = this.$refs.scrollSlider;
            if (!(box && slider)) return; // might be empty history panel

            const maxHeight = slider.clientHeight - box.clientHeight;

            // new scrolltop represented by new cursor
            // scrolltop should represent the height of the first displayed
            // row of the content in relation to the total number of rows in
            // the result set
            const newScrollTop = 1.0 * maxHeight * newCursor;

            // existing scrolltop
            const existingScrollTop = box.scrollTop;

            // this is how far we need to adjust
            // If we're off by more than fudge, schedule an event-free adjustment
            // to make it visually look right
            const fudge = this.getFirstRowHeight();
            const adjustment = Math.abs(newScrollTop - existingScrollTop);
            if (adjustment > fudge) {
                this.log("adjustScrollTop", newCursor, newScrollTop, adjustment);
                this.setScrollTop(newScrollTop);
            }
        },

        getFirstRowHeight() {
            const rowHeight = this.$refs?.listing.querySelector("ul > li")?.offsetHeight || 10;
            return parseInt(rowHeight);
        },

        setScrollTop(newScrollTop) {
            this.suppressEvents = true;
            if (this.suppressionTimeout) {
                clearTimeout(this.suppressionTimeout);
                this.suppressionTimeout = null;
            }

            this.log("setScrollTop", newScrollTop, this.suppressionPeriod);

            const box = this.$refs.scrollSliderContainer;
            box.scrollTop = Math.floor(newScrollTop);

            this.suppressionTimeout = setTimeout(() => {
                this.log("unsupressing");
                this.suppressEvents = false;
            }, this.suppressionPeriod);
        },

        // Determine whether the scrollbar is showing on the actual list,
        // this value is used to toggle the overlay scroller on/off

        checkScrollbars() {
            this.sbWidth = this.scrollBarWidth("listing");
        },

        scrollBarWidth(refName) {
            const listing = this.$refs?.[refName];
            if (!listing) return 0;
            // offset width includes scrollbar, clientWidth does not
            return listing.offsetWidth - listing.clientWidth;
        },
    },
};
</script>

<style lang="scss">
.scrollContainer {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;

    .listing,
    .scrollSliderContainer {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
    }

    .listing {
        overflow-y: scroll;
        z-index: 0;

        &::-webkit-scrollbar,
        &::-webkit-scrollbar-track,
        &::-webkit-scrollbar-thumb {
            background-color: transparent;
        }
    }

    .scrollSliderContainer {
        left: unset;
        overflow-y: scroll;
        z-index: 1;
        > div {
            height: 5000px;
        }
    }

    ul {
        list-style: none;
    }

    ul,
    li {
        padding: 0;
        margin: 0;
    }
}
</style>
