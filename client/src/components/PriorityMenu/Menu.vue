<template>
    <div class="priority-menu">
        <!-- primary menu, wraps each item in a LI for the flexbox and
        puts an intersect around the whole thing to monitor menu items coming
        and going -->
        <Intersect @enter="onShowItem" @leave="onHideItem" @destroy="onItemDestroy">
            <WrapChildren class="primary" :style="requiresFixedHeight">
                <slot name="default"></slot>
            </WrapChildren>
        </Intersect>

        <!-- overflow-->
        <slot name="overflow" :overflow="overflow">
            <div class="overflow" v-if="overflow.length">
                <b-dropdown no-caret right variant="link" size="sm" boundary="window" toggle-class="p-1">
                    <template v-slot:button-content>
                        <i class="fas fa-ellipsis-v" />
                        <span class="sr-only">...</span>
                    </template>
                    <b-dropdown-item v-for="item in overflow" :key="item.key" v-bind="item.attrs" v-on="item.on">
                        {{ item.attrs.title }}
                    </b-dropdown-item>
                </b-dropdown>
            </div>
        </slot>
    </div>
</template>

<script>
import WrapChildren from "./WrapChildren";
import Intersect from "./Intersect";

export default {
    components: {
        WrapChildren,
        Intersect,
    },
    props: {
        startingHeight: { type: Number, required: false, default: 50 },
    },
    data() {
        return {
            height: this.startingHeight,
            overflowKeys: new Set(),
        };
    },
    computed: {
        overflow() {
            return this.getVnodes()
                .filter((node) => this.overflowKeys.has(node.key))
                .map((node) => this.getMenuDataFromNode(node));
        },
        requiresFixedHeight() {
            return {
                height: `${this.height}px`,
            };
        },
    },
    methods: {
        onShowItem(key, entry) {
            this.setHeight(entry);
            this.removeFromOverflow(key);
        },
        onHideItem(key) {
            this.addToOverflow(key);
        },
        onItemDestroy(key) {
            this.removeFromOverflow(key);
        },

        setHeight(entry) {
            if (!entry) return;
            const {
                boundingClientRect: { height },
            } = entry;
            this.height = Math.max(this.height, height);
        },
        addToOverflow(key) {
            if (!this.overflowKeys.has(key)) {
                const newSet = new Set(this.overflowKeys);
                newSet.add(key);
                this.overflowKeys = newSet;
            }
        },
        removeFromOverflow(key) {
            if (this.overflowKeys.has(key)) {
                const newSet = new Set(this.overflowKeys);
                newSet.delete(key);
                this.overflowKeys = newSet;
            }
        },
        getVnodes() {
            const rawNodes = this.$slots.default || [];
            return rawNodes.filter((node) => node.tag);
        },
        // merge weird vnode attributes to get enough to generate a dropdown
        getMenuDataFromNode(vnode) {
            const componentOptions = vnode.componentOptions || {};
            const attrs = Object.assign({}, vnode.data.attrs || {}, componentOptions.propsData || {});
            const on = Object.assign({}, vnode.data.on || {}, componentOptions.listeners || {});
            return { attrs, on, key: vnode.key };
        },
    },
};
</script>

<style lang="scss">
/* standard list reset, which we should already
have but mysteriously dont */
ul,
li {
    list-style: none;
    padding: 0;
    margin: 0;
}

.priority-menu {
    position: relative;

    /* note this uses flex & flex-wrap to cleanly
    pop elements off the menu when the area is too
    narrow, but this demands a fixed height for the UL,
    which has to be set by javascript in the component. */

    .primary {
        display: flex;
        /* elements disappear onto next row which is invisible */
        flex-wrap: wrap;
        /* fix the height of the UL so that the overflow makes
        the 2nd row invisible. Doing so will cause the Intersect
        component to fire an event and put the item on the dropdown */
        overflow: hidden;
        /* right justified */
        justify-content: flex-end;
    }

    .primary > * {
        height: 100%;
    }
}

.priority-menu {
    display: flex;
}
</style>
