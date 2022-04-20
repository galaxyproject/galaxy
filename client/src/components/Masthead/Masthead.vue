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
                :active-tab="activeTab">
            </masthead-item>
        </b-navbar-nav>
        <div ref="quota-meter-container" class="quota-meter-container" />
    </b-navbar>
</template>

<script>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import { fetchMenu } from "layout/menu";
import { loadWebhookMenuItems } from "./_webhooks";

export default {
    name: "Masthead",
    components: {
        BNavbar,
        BNavbarBrand,
        BNavbarNav,
        MastheadItem,
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
            activeTab: null,
            baseTabs: [],
            extensionTabs: [],
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
            const scratchbookTabs = [this.mastheadState.frame.buttonActive, this.mastheadState.frame.buttonLoad];
            const tabs = [].concat(this.baseTabs, this.extensionTabs, scratchbookTabs);
            return tabs.map(this._tabToJson);
        },
    },
    created() {
        this.activeTab = this.initialActiveTab;
        this.baseTabs = fetchMenu(this.menuOptions);
        loadWebhookMenuItems(this.extensionTabs);
    },
    mounted() {
        this.mastheadState.quotaMeter.setElement(this.$refs["quota-meter-container"]);
        this.mastheadState.quotaMeter.render();
        const frames = this.mastheadState.frame.getFrames();
        frames
            .on("add remove", () => {
                const tab = this.mastheadState.frame.buttonLoad;
                tab.note = String(frames.length());
                tab.visible = frames.length() > 0;
                tab.show_note = frames.length() > 0;
            })
            .on("show hide", () => {
                this._reflectScratchbookFrames();
            });
    },
    methods: {
        addItem(item) {
            this.tabs.push(item);
        },
        highlight(activeTab) {
            this.activeTab = activeTab;
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
        _reflectScratchbookFrames() {
            const frames = this.mastheadState.frame.getFrames();
            const tab = this.mastheadState.frame.buttonLoad;
            tab.toggle = frames.visible;
            tab.icon = (frames.visible && "fa-eye") || "fa-eye-slash";
        },
    },
};
</script>
