<template>
    <b-navbar
        id="masthead"
        toggleable="lg"
        type="dark"
        role="navigation"
        aria-label="Main"
        class="justify-content-center"
    >
        <b-navbar-brand href="https://anvil.terra.bio" aria-label="homepage">
            <img alt="Galaxy Logo" class="navbar-brand-image align-middle" src="/static/images/galaxy_project_logo_white_square.png" />
            <img alt="Anvil Logo" class="navbar-brand-image align-middle" src="/static/images/anvilwhite.png" />
        </b-navbar-brand>

        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in tabs"
                :tab="tab"
                :active-tab="activeTab"
                :key="`tab-${idx}`"
                :app-root="appRoot"
                :galaxy="galaxy"
                v-show="!(tab.hidden === undefined ? false : tab.hidden)"
            >
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
    props: {
        displayGalaxyBrand: {
            type: Boolean,
            default: true,
        },
        brand: {
            type: String,
        },
        brandLink: {
            type: String,
        },
        brandImage: {
            type: String,
        },
        activeTab: {
            type: String,
        },
        mastheadState: {
            type: Object,
        },
        appRoot: {
            type: String,
        },
        galaxy: {
            type: Object,
        },
        menuOptions: {
            type: Object,
        },
    },
    components: {
        BNavbar,
        BNavbarBrand,
        BNavbarNav,
        MastheadItem,
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
    data() {
        return {
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
            const tabs = [].concat(this.baseTabs, scratchbookTabs, this.extensionTabs);
            return tabs.map(this._tabToJson);
        },
    },
    created() {
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
};
</script>

<style scoped></style>
