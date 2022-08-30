<template>
    <b-navbar id="masthead" type="dark" role="navigation" aria-label="Main" class="justify-content-center">
        <b-navbar-brand :href="brandLink" aria-label="homepage">
            <img alt="logo" class="navbar-brand-image" :src="brandImage" />
            <img v-if="brandImageSecondary" alt="logo" class="navbar-brand-image" :src="brandImageSecondary" />
            <span class="navbar-brand-title">{{ brandTitle }}</span>
        </b-navbar-brand>
        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in tabs"
                v-show="!(tab.hidden === undefined ? false : tab.hidden)"
                :key="`tab-${idx}`"
                :tab="tab"
                :active-tab="activeTab" />
            <masthead-item :tab="windowTab" :toggle="windowToggle" @click="onWindowToggle" />
        </b-navbar-nav>
        <quota-meter />
    </b-navbar>
</template>

<script>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import { loadWebhookMenuItems } from "./_webhooks";
import QuotaMeter from "./QuotaMeter.vue";

export default {
    name: "Masthead",
    components: {
        BNavbar,
        BNavbarBrand,
        BNavbarNav,
        MastheadItem,
        QuotaMeter,
    },
    props: {
        displayGalaxyBrand: {
            type: Boolean,
            default: true,
        },
        baseTabs: {
            type: Array,
            default: () => [],
        },
        brand: {
            type: String,
            default: null,
        },
        brandLink: {
            type: String,
            default: null,
        },
        brandImage: {
            type: String,
            default: null,
        },
        brandImageSecondary: {
            type: String,
            default: null,
        },
        initialActiveTab: {
            type: String,
            default: "analysis",
        },
        mastheadState: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            activeTab: this.initialActiveTab,
            extensionTabs: [],
            windowTab: this.mastheadState.windowManager.getTab(),
            windowToggle: false,
        };
    },
    watch: {
        $route() {
            this.updateTab();
        },
    },
    computed: {
        brandTitle() {
            let brandTitle = this.displayGalaxyBrand ? "Galaxy " : "";
            if (this.brand) {
                brandTitle += this.brand;
            }
            return brandTitle;
        },
        tabs() {
            const tabs = [].concat(this.baseTabs, this.extensionTabs);
            return tabs.map(this._tabToJson);
        },
    },
    created() {
        loadWebhookMenuItems(this.extensionTabs);
        this.updateTab();
    },
    methods: {
        addItem(item) {
            this.tabs.push(item);
        },
        updateTab() {
            const currentRoute = this.$route?.path;
            let matchedId = null;
            for (const tab of this.baseTabs) {
                const tabId = tab.id;
                if (currentRoute == `/${tab.url}`) {
                    matchedId = tabId;
                    break;
                } else if (tab.menu) {
                    for (const item of tab.menu) {
                        if (currentRoute == `/${item.url}`) {
                            matchedId = tabId;
                            break;
                        }
                    }
                }
            }
            this.activeTab = matchedId || this.activeTab;
            return this.activeTab;
        },
        onWindowToggle() {
            this.windowToggle = !this.windowToggle;
        },
        _tabToJson(el) {
            const defaults = {
                target: "_parent",
            };
            let asJson;
            if (el.toJSON instanceof Function) {
                asJson = el.toJSON();
            } else {
                asJson = el;
            }
            return Object.assign({}, defaults, asJson);
        },
    },
};
</script>
