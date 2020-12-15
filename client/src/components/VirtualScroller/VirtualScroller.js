import inViewport from "in-viewport";
import Scroll from "./Scroll";
import { cssLength, notNegative } from "./util";
import "./scroller.scss";

export default {
    directives: { Scroll },

    props: {
        keyField: { type: String, required: true },
        scrollDebounce: { type: Number, required: false, default: 250 },
        itemHeight: { required: true, validator: notNegative },
        items: { type: Array, required: true },
        topPlaceholders: { type: Number, default: 0 },
        bottomPlaceholders: { type: Number, default: 0 },
        suppressionPeriod: { type: Number, default: 250 },
        scrollTo: { default: null },
    },

    data() {
        return {
            scrollTop: 0,
        };
    },

    computed: {
        contentStyle() {
            return {
                paddingTop: cssLength(this.topPlaceholders * this.itemHeight),
                paddingBottom: cssLength(this.bottomPlaceholders * this.itemHeight),
            };
        },

        cursor() {
            if (this.scrollTop > 0) {
                const height = this.getRefProp("content", "clientHeight", 0);
                if (undefined !== height && height > 0) {
                    return (1.0 * this.scrollTop) / height;
                }
            }
            return 0;
        },

        scrollEventPayload() {
            const el = this.getFirstVisibleElement();
            return {
                cursor: this.cursor,
                key: el?.dataset.key,
                keyIndex: el?.dataset.index,
            };
        },
    },

    watch: {
        scrollEventPayload(payload) {
            if (!this._suppressScrollEvent) {
                this.$emit("scroll", payload);
            }
        },

        scrollTo(val) {
            this.suppress();
            this.$nextTick(() => {
                const { scrollToMe, container } = this.$refs;
                const doScroll =
                    scrollToMe && val && scrollToMe.dataset.key == val && !inViewport(scrollToMe, { container });
                if (doScroll) {
                    scrollToMe.scrollIntoView(true);
                }
                setTimeout(() => this.unsuppress(), 100);
            });
        },
    },

    methods: {
        onScroll() {
            this.scrollTop = this.$refs.container.scrollTop;
        },

        //#region Dom Utils

        getScrollTop(refName = "container") {
            return this.getRefProp(refName, "scrollTop");
        },

        getRefProp(refName, propName, defaultVal = undefined) {
            if (refName in this.$refs) {
                if (propName in this.$refs[refName]) {
                    return this.$refs[refName][propName];
                }
            }
            return defaultVal;
        },

        getRowElementByKey(key) {
            if (this.$refs.contentlist) {
                const list = Array.from(this.$refs.contentlist.children);
                return list.find((el) => el.dataset.key == key);
            }
            return undefined;
        },

        getFirstVisibleElement() {
            const { container, contentlist } = this.$refs;
            let result = undefined;
            if (container && contentlist) {
                for (const row of contentlist.children) {
                    if (inViewport(row, { container })) {
                        result = row;
                        break;
                    }
                }
            }
            return result;
        },

        //#endregion

        //#region Event suppression

        suppress() {
            this._suppressScrollEvent = true;
        },

        unsuppress() {
            if (this._suppressTimeoutId) {
                clearTimeout(this._suppressTimeoutId);
                this._suppressTimeoutId = null;
            }
            this._suppressTimeoutId = setTimeout(() => {
                this._suppressScrollEvent = false;
            }, this.suppressionPeriod);
        },

        //#endregion

        //#region Rendering

        renderList() {
            return this.items.map(this.renderItem);
        },

        renderItem(item, index) {
            const h = this.$createElement;
            const key = item[this.keyField];
            const slotChild = this.renderSlot("default", { key, index, item });

            let ref = undefined;
            let staticClass = "";
            if (key == this.scrollTo) {
                ref = "scrollToMe";
                staticClass = "scrollToMe";
            }

            const attrs = {
                // index considering the missing data rows reprsented by topPlaceholders
                "data-index": index + this.topPlaceholders,
                // index with respect to the passed items array
                "item-index": index,
                "data-key": key,
            };

            return h("li", { key, ref, staticClass, attrs }, slotChild);
        },

        renderSlot(name = "default", data, optional = false) {
            if (this.$scopedSlots[name]) {
                return this.$scopedSlots[name](data instanceof Function ? data() : data);
            } else if (this.$slots[name] && (!data || optional)) {
                return this.$slots[name];
            }
            return undefined;
        },

        //#endregion

        //#region Debugging

        report(label) {
            console.groupCollapsed(label);
            console.log("scrollTo", this.scrollTo);
            console.log("items.length", this.items.length);
            if (this.items.length > 0) {
                const list = this.items;
                console.log("items", `${list[0].hid} -> ${list[list.length - 1].hid}`);
            }
            console.log("topPlaceholders", this.topPlaceholders);
            console.log("bottomPlaceholders", this.bottomPlaceholders);
            console.groupEnd();
        },

        //#endregion
    },

    render(h) {
        // content list
        const list = h(
            "ul",
            {
                ref: "contentlist",
            },
            this.renderList()
        );

        // contains all the content + padding
        const content = h(
            "div",
            {
                ref: "content",
                staticClass: "scrollContent",
                style: this.contentStyle,
                attrs: {
                    "data-top-rows": this.topPlaceholders,
                    "data-bottom-rows": this.bottomPlaceholders,
                },
            },
            [list]
        );

        // outer container, scrollTop lives here
        const container = h(
            "div",
            {
                ref: "container",
                staticClass: "virtualScroller",
                directives: [
                    {
                        name: "scroll",
                        modifiers: { self: true },
                        value: this.onScroll,
                    },
                ],
            },
            [content]
        );

        return container;
    },
};
