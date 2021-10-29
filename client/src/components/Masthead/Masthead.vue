<template>
    <b-navbar id="masthead" type="dark" role="navigation" aria-label="Main" class="justify-content-center">
        <b-navbar-brand @click="showNavGuard" :href="anvilLink" aria-label="homepage">
            <img alt="Galaxy Logo" style="padding-top: 0.4rem;" class="navbar-brand-image" :src="galaxyLogoSrc" />
            <img alt="Anvil Logo" class="navbar-brand-image" :src="anvilLogoSrc" />
        </b-navbar-brand>

        <b-modal ref="navGuardModal" hide-footer title="A quick note before you go">
            <div>
                <p>
                    You are navigating away from Galaxy, which will continue to run in the background. Any jobs you have
                    running will continue, but it's important to keep in mind that this instance will also continue
                    potentially incurring costs. Remember to shut down Galaxy when you are done.
                </p>
                <p>
                    This modal will not be shown again.
                </p>
            </div>
            <b-button variant="primary" block @click="confirmNav">
                I understand, take me back to my AnVIL Dashboard
            </b-button>
        </b-modal>

        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in tabs"
                :tab="tab"
                :active-tab="activeTab"
                :key="`tab-${idx}`"
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
import { getAppRoot } from "onload/loadConfig";

export default {
    name: "Masthead",
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
        showNavGuard(ev) {
            const dismissNavGuard = localStorage.getItem("dismissNavGuard");
            if (!dismissNavGuard === true) {
                this.$refs.navGuardModal.show();
                ev.preventDefault();
            }
        },
        confirmNav() {
            localStorage.setItem("dismissNavGuard", true);
            window.location = this.anvilLink;
        },
    },
    data() {
        return {
            activeTab: null,
            baseTabs: [],
            extensionTabs: [],
            anvilLink: "https://anvil.terra.bio",
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
        anvilLogoSrc() {
            return `${getAppRoot()}static/images/anvilwhite.png`;
        },
        galaxyLogoSrc() {
            return `${getAppRoot()}static/images/galaxy_project_logo_white_square.png`;
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
};
</script>
