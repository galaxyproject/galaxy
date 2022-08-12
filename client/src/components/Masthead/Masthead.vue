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
import { fetchMenu } from "layout/menu";
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
            default: null,
        },
        mastheadState: {
            type: Object,
            default: null,
        },
        menuOptions: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            activeTab: this.initialActiveTab,
            baseTabs: [],
            extensionTabs: [],
            windowTab: this.mastheadState.windowManager.getTab(),
            windowToggle: false,
        };
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
        this.baseTabs = fetchMenu(this.menuOptions);
        loadWebhookMenuItems(this.extensionTabs);
    },
    methods: {
        addItem(item) {
            this.tabs.push(item);
        },
        highlight(activeTab) {
            this.activeTab = activeTab;
        },
        onWindowToggle() {
            this.windowToggle = !this.windowToggle;
        },
        _tabToJson(el) {
            const defaults = {
                visible: true,
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
