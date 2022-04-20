<template>
    <b-nav-item
        v-if="!menu"
        :id="tab.id"
        v-b-tooltip.hover.bottom
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        :class="classes"
        :style="styles"
        :href="formatUrl(tab.url)"
        :target="tab.target || '_parent'"
        role="menuitem"
        :link-classes="linkClasses"
        :title="tab.tooltip"
        @click="open(tab, $event)">
        <template v-if="tab.icon">
            <span :class="iconClasses" />
            <span v-if="tab.show_note" :class="['nav-note', tab.note_cls]">{{ tab.note }}</span>
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
        :style="styles"
        :text="tab.title"
        href="#"
        :title="tab.tooltip"
        @show="open(tab, $event)">
        <template v-for="(item, idx) in tab.menu">
            <div v-if="item.divider" :key="`divider-${idx}`" class="dropdown-divider" />
            <b-dropdown-item
                v-else-if="item.hidden !== true"
                :key="`item-${idx}`"
                :href="formatUrl(item.url)"
                :target="item.target || '_parent'"
                role="menuitem"
                :disabled="item.disabled === true"
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
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";

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
        },
        activeTab: {
            type: String,
        },
    },
    computed: {
        menu() {
            return this.tab.menu;
        },
        popoverNote() {
            return `Please <a href="${getAppRoot()}login">login or register</a> to use this feature.`;
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
                toggle: this.tab.toggle,
            };
        },
        iconClasses() {
            return Object.fromEntries([
                ["fa fa-fw", true],
                [this.tab.icon, this.tab.icon],
            ]);
        },
        styles() {
            return {
                visibility: this.tab.visible ? "visible" : "hidden",
            };
        },
        galaxyIframe() {
            return document.getElementById("galaxy_main");
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
        open(tab, event) {
            if (tab.onclick) {
                return this.propogateClick(tab, event);
            }
            if (tab.disabled) {
                event.preventDefault();
                this.$root.$emit("bv::hide::tooltip");
                this.$root.$emit("bv::show::popover", tab.id);
                setTimeout(() => {
                    this.$root.$emit("bv::hide::popover", tab.id);
                }, 3000);
            } else if (!tab.menu) {
                event.preventDefault();
                const galaxy = getGalaxyInstance();
                if (tab.target === "__use_router__" && typeof galaxy.page !== "undefined") {
                    galaxy.page.router.executeUseRouter(this.formatUrl(tab.url));
                } else {
                    try {
                        galaxy.frame.add({ ...tab, url: this.formatUrl(tab.url) });
                    } catch (err) {
                        console.warn("Missing frame element on galaxy instance", err);
                    }
                }
            }
        },
        propogateClick(tab, event) {
            event.preventDefault();
            tab.onclick();
            if (tab.id === "enable-scratchbook") {
                this.$emit("updateScratchbookTab", tab);
            }
        },
        formatUrl(url) {
            if (typeof url === "string" && url.indexOf("//") === -1 && url.charAt(0) != "/") {
                return getAppRoot() + url;
            } else {
                return url;
            }
        },
    },
};
</script>
