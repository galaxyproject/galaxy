<template>
        <div>
            <b-navbar id="masthead" toggleable="lg" type="dark"
                      role="navigation" aria-label="Main" class="justify-content-center">
                <b-navbar-brand :href="brandLink" aria-label="homepage">
                    <img alt="logo" class="navbar-brand-image" :src="brandImage"/>
                    <span class="navbar-brand-title">{{ brandTitle }}</span>
                </b-navbar-brand>

                <b-navbar-nav>
                    <template v-for="tab in tabs">
                            <b-nav-item v-if="!tab.menu"
                                        :class="{
                                            active: tab.id === activeTab,
                                        }"
                                        :active="!tab.disabled"
                                        v-b-tooltip.hover.bottom :title="tab.tooltip"
                                        @click="open(tab, $event)"
                                        v-b-popover.manual.bottom="{id: tab.id, content: popoverNote, html: true}"
                                        :style="{
                                            visibility: tab.visible ? 'visible' : 'hidden',
                                        }"
                                        :id="tab.id"
                                        :href="tab.url"
                                        :target="tab.target"
                                        :link-classes="[tab.icon && 'nav-icon', tab.icon && 'fa', tab.icon || '']"
                            >

                                {{ tab["title"] }}
                                <div v-if="tab.show_note" class="nav-note-port">{{ tab["note"] }}</div>
                            </b-nav-item>

                            <b-nav-item-dropdown v-else
                                                 :text="tab.title"
                                                 v-b-tooltip.hover.bottom :title="tab.tooltip"
                                                 @show="open(tab, $event)"
                                                 v-b-popover.manual.bottom="{id: tab.id, content: popoverNote, html: true}"
                                                 :style="{visibility: tab.visible ? 'visible' : 'hidden'}"
                                                 :id="tab.id" href="#">
                                <b-dropdown-item v-for="item in tab.menu"
                                                 :href="item.url"
                                                 :target="item.target"
                                                 @click="open(item, $event)"
                                >
                                    {{ item["title"] }}
                                    <div v-if="tab.note" class="nav-note-port">{{ tab["note"] }}</div>
                                </b-dropdown-item>
                            </b-nav-item-dropdown>
                    </template>
                </b-navbar-nav>

                <div ref="quota-meter-container" class="quota-meter-container"/>
            </b-navbar>
        </div>
</template>

<script>
    import { VBTooltip } from "bootstrap-vue";
    import { VBPopover } from "bootstrap-vue";
    import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";

    export default {
        name: "Masthead",
        directives: {
            "v-b-tooltip": VBTooltip,
            "v-b-popover": VBPopover
        },
        props: {
            brandTitle: {
                type: String
            },
            brandLink: {
                type: String
            },
            brandImage: {
                type: String
            },
            quotaMeter: {
                type: Object
            },
            activeTab: {
                type: String,
            },
            tabs: {
                type: Array
            },
            appRoot: {
                type: String,
            },
            Galaxy: {
                type: Object,
            }
        },
        components: {
            BNavbar,
            BNavbarBrand,
            BNavbarNav,
        },
        data() {
            return {
            };
        },
        computed: {
            popoverNote() {
                return `Please <a href="${this.appRoot}login">login or register</a> to use this feature.`;
            }
        },
        methods: {
            open(tab, event) {
                if (tab.disabled) {
                    event.preventDefault();

                    this.$root.$emit('bv::hide::tooltip');
                    this.$root.$emit('bv::show::popover', tab.id);

                    setTimeout(() => {
                        this.$root.$emit('bv::hide::popover', tab.id);
                    }, 3000);
                } else if (!tab.menu) {
                    event.preventDefault();

                    if (tab.target === "__use_router__" && typeof this.Galaxy.page !== "undefined") {
                        this.Galaxy.page.router.executeUseRouter(tab.url);
                    } else {
                        try {
                            this.Galaxy.frame.add(tab);
                        } catch (err) {
                            console.warn("Missing frame element on galaxy instance", err);
                        }
                    }
                }
            },
        },
        mounted() {
            console.log(this.tabs);
            this.quotaMeter.setElement(this.$refs['quota-meter-container']);
            this.quotaMeter.render();
        }
    }
</script>

<style scoped>
    .nav-note-port {
        position: absolute;
        bottom: .1rem;
        font-size: .7rem;
        color: gold;
    }
</style>
