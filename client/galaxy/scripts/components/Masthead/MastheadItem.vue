<template>
    <b-nav-item
        v-if="!menu"
        :class="classes"
        :style="styles"
        :active="!tab.disabled"
        :id="tab.id"
        :href="formatUrl(tab.url)"
        :target="tab.target || '_parent'"
        role="menuitem"
        :link-classes="linkClasses"
        v-b-tooltip.hover.bottom
        :title="tab.tooltip"
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        @click="open(tab, $event)"
    >
        <template v-if="tab.icon">
            <span :class="iconClasses" />
            <span v-if="tab.show_note" :class="['nav-note-port', tab.note_cls]">{{ tab.note }}</span>
        </template>
        <template v-else>
            {{ tab.title }}
        </template>
    </b-nav-item>
    <b-nav-item-dropdown
        ref="dropdown"
        v-else
        :class="classes"
        :style="styles"
        :text="tab.title"
        :id="tab.id"
        href="#"
        v-b-tooltip.hover.bottom
        :title="tab.tooltip"
        v-b-popover.manual.bottom="{ id: tab.id, content: popoverNote, html: true }"
        @show="open(tab, $event)"
    >
        <template v-for="(item, idx) in tab.menu">
            <b-dropdown-item
                :href="formatUrl(item.url)"
                :key="`item-${idx}`"
                :target="item.target || '_parent'"
                role="menuitem"
                @click="open(item, $event)"
            >
                {{ item.title }}
            </b-dropdown-item>
            <div v-if="item.divider" class="dropdown-divider" :key="`divider-${idx}`" />
        </template>
    </b-nav-item-dropdown>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import { VBPopover } from "bootstrap-vue";
import { BNavItem, BNavItemDropdown, BDropdownItem } from "bootstrap-vue";

export default {
    name: "MastheadItem",
    components: {
        BNavItem,
        BNavItemDropdown,
        BDropdownItem,
    },
    directives: {
        "v-b-tooltip": VBTooltip,
        "v-b-popover": VBPopover,
    },
    props: {
        tab: {
            type: Object,
        },
        activeTab: {
            type: String,
        },
        appRoot: {
            type: String,
        },
        Galaxy: {
            type: Object,
        },
    },
    computed: {
        menu() {
            return this.tab.menu;
        },
        active() {
            return this.tab.id == this.activeTab;
        },
        popoverNote() {
            return `Please <a href="${this.appRoot}login">login or register</a> to use this feature.`;
        },
        classes() {
            let classesString = this.tab.cls || "";
            if (this.active) {
                classesString = `${classesString} active`;
            }
            return classesString;
        },
        linkClasses() {
            return {
                "nav-icon": this.tab.icon,
            };
        },
        iconClasses() {
            return Object.fromEntries([
                ["fa", true],
                ["toggle", this.tab.toggle],
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
    created() {
        if (this.tab.onbeforeunload) {
            document.addEventListener("beforeunload", () => {
                this.tab.onbeforeunload();
            });
        }
    },
    mounted() {
        if (this.galaxyIframe) {
            this.galaxyIframe.addEventListener("load", this.iframeListener);
        }
    },
    destroyed() {
        if (this.galaxyIframe) {
            this.galaxyIframe.removeEventListener("load", this.iframeListener);
        }
    },
    methods: {
        iframeListener() {
            return this.galaxyIframe.contentDocument.addEventListener("click", this.hideDropdown);
        },
        hideDropdown() {
            if (this.$refs.dropdown) this.$refs.dropdown.hide();
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
                if (tab.target === "__use_router__" && typeof this.Galaxy.page !== "undefined") {
                    this.Galaxy.page.router.executeUseRouter(this.formatUrl(tab.url));
                } else {
                    try {
                        this.Galaxy.frame.add({ ...tab, url: this.formatUrl(tab.url) });
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
            return typeof url === "string" && url.indexOf("//") === -1 && url.charAt(0) != "/"
                ? this.appRoot + url
                : url;
        },
    },
};
</script>

<style scoped>
.nav-note-port {
    position: absolute;
    font-weight: 700;
    font-size: 0.7rem;
    color: gold;
    line-height: 3.5rem;
    margin-left: 1px;
}

li .nav-link > span.toggle {
    color: gold;
}
</style>
