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
                                            active: tab.id === activeTab(),
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
                                        :link-classes="[
                                            tab.toggle && 'toggle',
                                            tab.icon && 'nav-icon',
                                            tab.icon && 'fa',
                                            tab.icon || ''
                                        ]">

                                {{ tab["title"] }}
                            </b-nav-item>
                            <b-nav-item-dropdown v-else
                                                 :class="{
                                                    active: tab.id === activeTab(),
                                                 }"
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
                                </b-dropdown-item>
                            </b-nav-item-dropdown>
                        <li v-if="tab.show_note" class="nav-note-port" :class="tab.note_cls">{{ tab["note"] }}</li>
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
    import _ from "underscore";

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
                type: Function,
            },
            tabs: {
                type: Array
            },
            frames: {
                type: Object,
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
                if (tab.onclick) {
                    return this.propogateClick(tab, event);
                }

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
            propogateClick(tab, event) {
                event.preventDefault();
                tab.onclick();

                if (tab.id === "enable-scratchbook") {
                    _.each(this.tabs, (tab, i) => {
                        if (tab.id === "enable-scratchbook") {
                            tab.active = !tab.active;

                            this.$set(this.tabs, i, {
                                ...tab,
                                toggle: tab.active,
                                show_note: tab.active,
                                note_cls: tab.active && "fa fa-check"
                            });
                        }
                    });
                }
            },
        },
        created() {
            _.each(this.tabs, tab => {
                if (tab.onbeforeunload) {
                    document.addEventListener('beforeunload', () => {
                        tab.onbeforeunload();
                    });
                }
            });
        },
        mounted() {
            this.quotaMeter.setElement(this.$refs['quota-meter-container']);
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
                        icon: (this.frames.visible && "fa-eye") || "fa-eye-slash"
                    });
                });
        }
    }
</script>

<style scoped>
    .nav-note-port {
        position: relative;
        font-weight: 700;
        left: -0.4rem;
        top: 0.7rem;
        font-size: .7rem;
        color: gold;
        width: 0;
    }
</style>
