<template>
    <b-navbar
        id="masthead"
        toggleable="lg"
        type="dark"
        role="navigation"
        aria-label="Main"
        class="justify-content-center"
    >
        <b-navbar-brand :href="brandLink" aria-label="homepage">
            <img alt="logo" class="navbar-brand-image" :src="brandImage" />
            <span class="navbar-brand-title">{{ brandTitle }}</span>
        </b-navbar-brand>

        <b-navbar-nav>
            <masthead-item
                v-for="(tab, idx) in tabs"
                :tab="tab"
                :activeTab="activeTab"
                :key="`tab-${idx}`"
                :appRoot="appRoot"
                :Galaxy="Galaxy"
                v-show="!(tab.hidden === undefined ? false : tab.hidden)"
                @updateScratchbookTab="updateScratchbookTab"
            >
            </masthead-item>
        </b-navbar-nav>

        <div ref="quota-meter-container" class="quota-meter-container" />
    </b-navbar>
</template>

<script>
import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";
import MastheadItem from "./MastheadItem";
import _ from "underscore";

export default {
    name: "Masthead",
    props: {
        brandTitle: {
            type: String,
        },
        brandLink: {
            type: String,
        },
        brandImage: {
            type: String,
        },
        quotaMeter: {
            type: Object,
        },
        activeTab: {
            type: String,
        },
        tabs: {
            type: Array,
        },
        frames: {
            type: Object,
        },
        appRoot: {
            type: String,
        },
        Galaxy: {
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
        updateScratchbookTab(tab) {
            _.each(this.tabs, (tab, i) => {
                if (tab.id === "enable-scratchbook") {
                    tab.active = !tab.active;

                    this.$set(this.tabs, i, {
                        ...tab,
                        toggle: tab.active,
                        show_note: tab.active,
                        note_cls: tab.active && "fa fa-check",
                    });
                }
            });
        },
    },
    mounted() {
        this.quotaMeter.setElement(this.$refs["quota-meter-container"]);
        this.quotaMeter.render();

        const idx = _.findIndex(this.tabs, { id: "show-scratchbook" });
        this.frames
            .on("add remove", () => {
                this.$set(this.tabs, idx, {
                    ...this.tabs[idx],
                    note: this.frames.length(),
                    visible: this.frames.length() > 0,
                    show_note: this.frames.length() > 0,
                });
            })
            .on("show hide", () => {
                this.$set(this.tabs, idx, {
                    ...this.tabs[idx],
                    toggle: this.frames.visible,
                    icon: (this.frames.visible && "fa-eye") || "fa-eye-slash",
                });
            });
    },
};
</script>

<style scoped></style>
