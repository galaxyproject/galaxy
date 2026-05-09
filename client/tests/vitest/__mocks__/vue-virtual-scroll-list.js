// Mock for vue-virtual-scroll-list which calls Vue.component at module load
// (Vue 2 global API). For tests we don't need real virtual scrolling --
// just render every data-source through the data-component so test
// assertions can find the rendered items.

import { defineComponent, h } from "vue";

const VirtualList = defineComponent({
    name: "VirtualList",
    props: {
        dataKey: { type: String, required: true },
        dataSources: { type: Array, default: () => [] },
        dataComponent: { type: Object, required: true },
        extraProps: { type: Object, default: () => ({}) },
        // Catch-all for the rest of the props the real lib accepts; we ignore them.
        estimateSize: { type: Number, default: 50 },
        keeps: { type: Number, default: 30 },
        direction: { type: String, default: "vertical" },
        itemClass: { type: String, default: "" },
        itemStyle: { type: Object, default: () => ({}) },
        wrapClass: { type: String, default: "" },
        wrapStyle: { type: Object, default: () => ({}) },
    },
    render() {
        return h(
            "div",
            { class: this.wrapClass, style: this.wrapStyle },
            this.dataSources.map((source) =>
                h(this.dataComponent, {
                    key: source[this.dataKey],
                    source,
                    ...this.extraProps,
                    class: this.itemClass,
                    style: this.itemStyle,
                }),
            ),
        );
    },
});

export default VirtualList;
