<template>
    <b-nav-item
        v-if="!menu"
        :id="tab.id"
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        :class="classes"
        :href="getPath(tab.url)"
        :target="tab.target || '_parent'"
        :link-classes="linkClasses"
        :title="tab.tooltip"
        @click="open(tab, $event)">
        <template v-if="tab.icon">
            <!-- If this is an icon-based tab, inject tooltip directly for screen readers -->
            <span class="sr-only">{{ tab.tooltip || tab.id }}</span>
            <span :class="iconClasses" />
            <span v-if="toggle" class="nav-note fa fa-check" />
        </template>
        <template v-else>
            {{ tab.title }}
        </template>
    </b-nav-item>
    <b-nav-item-dropdown
        v-else
        :id="tab.id"
        ref="dropdown"
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        :class="classes"
        :text="tab.title"
        href="#"
        :title="tab.tooltip"
        @show="open(tab, $event)">
        <template v-for="(item, idx) in tab.menu">
            <div v-if="item.divider" :key="`divider-${idx}`" class="dropdown-divider" />
            <b-dropdown-item
                v-else-if="item.hidden !== true"
                :key="`item-${idx}`"
                :href="getPath(item.url)"
                :target="item.target || '_parent'"
                role="menuitem"
                :active="item.disabled"
                :disabled="item.disabled"
                @click="open(item, $event)">
                {{ item.title }}
            </b-dropdown-item>
        </template>
    </b-nav-item-dropdown>
</template>

<script>
import Vue from "vue";
import { VBPopoverPlugin, VBTooltipPlugin } from "bootstrap-vue";
import { BNavItem, BNavItemDropdown, BDropdownItem } from "bootstrap-vue";
import { safePath } from "utils/redirect";

Vue.use(VBPopoverPlugin);
Vue.use(VBTooltipPlugin);

export default {
    name: "MastheadItem",
    components: {
        BNavItem,
        BNavItemDropdown,
        BDropdownItem,
    },
    props: {
        tab: {
            type: Object,
            default: null,
        },
        toggle: {
            type: Boolean,
            default: false,
        },
        activeTab: {
            type: String,
            default: null,
        },
    },
    computed: {
        menu() {
            return this.tab.menu;
        },
        popoverNote() {
            return `Please <a href="${safePath("/login")}">log in or register</a> to use this feature.`;
        },
        classes() {
            const isActiveTab = this.tab.id == this.activeTab;
            return Object.fromEntries([
                ["active", isActiveTab],
                [this.tab.cls, true],
            ]);
        },
        linkClasses() {
            return {
                "nav-icon": this.tab.icon,
                toggle: this.toggle,
            };
        },
        iconClasses() {
            return Object.fromEntries([
                ["fa fa-fw", true],
                [this.tab.icon, this.tab.icon],
            ]);
        },
    },
    mounted() {
        window.addEventListener("blur", this.hideDropdown);
    },
    destroyed() {
        window.removeEventListener("blur", this.hideDropdown);
    },
    methods: {
        hideDropdown() {
            if (this.$refs.dropdown) {
                this.$refs.dropdown.hide();
            }
        },
        getPath(url) {
            return safePath(url);
        },
        open(tab, event) {
            if (tab.onclick) {
                event.preventDefault();
                tab.onclick();
                this.$emit("click");
            } else if (tab.disabled) {
                event.preventDefault();
                this.$root.$emit("bv::hide::tooltip");
                this.$root.$emit("bv::show::popover", tab.id);
                setTimeout(() => {
                    this.$root.$emit("bv::hide::popover", tab.id);
                }, 3000);
            } else if (!tab.menu) {
                event.preventDefault();
                this.$emit("open-url", { ...tab });
            }
        },
    },
};
</script>
