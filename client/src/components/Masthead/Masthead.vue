<template>
    <b-navbar id="masthead" type="dark" role="navigation" aria-label="Main" class="justify-content-center">
        <b-navbar-brand :href="getPath(logoUrl)" aria-label="homepage">
            <img alt="logo" class="navbar-brand-image" :src="getPath(logoSrc)" />
            <img v-if="logoSrcSecondary" alt="logo" class="navbar-brand-image" :src="getPath(logoSrcSecondary)" />
            <span class="navbar-brand-title">{{ brandTitle }}</span>
        </b-navbar-brand>
        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in allTabs"
                v-show="tab.hidden !== true"
                :key="`tab-${idx}`"
                :tab="tab"
                :active-tab="activeTab"
                @open-url="$emit('open-url', $event)" />
            <masthead-item v-if="windowTab" :tab="windowTab" :toggle="windowToggle" @click="onWindowToggle" />
        </b-navbar-nav>
        <quota-meter />
    </b-navbar>
</template>

<script>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import { loadWebhookMenuItems } from "./_webhooks";
import QuotaMeter from "./QuotaMeter.vue";
import { safePath } from "utils/redirect";
import { getActiveTab } from "./utilities";

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
        tabs: {
            type: Array,
            default: () => [],
        },
        brand: {
            type: String,
            default: null,
        },
        initialActiveTab: {
            type: String,
            default: "analysis",
        },
        logoUrl: {
            type: String,
            default: null,
        },
        logoSrc: {
            type: String,
            default: null,
        },
        logoSrcSecondary: {
            type: String,
            default: null,
        },
        windowTab: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            activeTab: this.initialActiveTab,
            extensionTabs: [],
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
        allTabs() {
            return [].concat(this.tabs, this.extensionTabs);
        },
    },
    watch: {
        $route() {
            this.updateTab();
        },
    },
    created() {
        loadWebhookMenuItems(this.extensionTabs);
        this.updateTab();
    },
    methods: {
        addItem(item) {
            this.allTabs.push(item);
        },
        getPath(url) {
            return safePath(url);
        },
        updateTab() {
            const currentRoute = this.$route?.path;
            this.activeTab = getActiveTab(currentRoute, this.tabs) || this.activeTab;
        },
        onWindowToggle() {
            this.windowToggle = !this.windowToggle;
        },
    },
};
</script>
