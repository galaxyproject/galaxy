<template>
    <b-nav-item v-if="!tab.menu"
                :class="{ active: tab.id === activeTab(), }"
                :active="!tab.disabled"
                v-b-tooltip.hover.bottom :title="tab.tooltip"
                @click="open(tab, $event)"
                v-b-popover.manual.bottom="{id: tab.id, content: popoverNote, html: true}"
                :style="{ visibility: tab.visible ? 'visible' : 'hidden',}"
                :id="tab.id"
                :href="tab.url"
                :target="tab.target"
                :link-classes="[ tab.icon && 'nav-icon', ]">

        <template v-if="tab.icon">
            <span :class="['fa', tab.icon, tab.toggle && 'toggle']"/>
            <span v-if="tab.show_note" class="nav-note-port" :class="tab.note_cls">{{ tab.note }}</span>
        </template>
        <template v-else>
            {{ tab.title }}
        </template>
    </b-nav-item>
    <b-nav-item-dropdown v-else
                         :class="{ active: tab.id === activeTab(), }"
                         :text="tab.title"
                         v-b-tooltip.hover.bottom :title="tab.tooltip"
                         @show="open(tab, $event)"
                         v-b-popover.manual.bottom="{id: tab.id, content: popoverNote, html: true}"
                         :style="{visibility: tab.visible ? 'visible' : 'hidden'}"
                         :id="tab.id" href="#">
        <template v-for="item in tab.menu">
            <b-dropdown-item :href="item.url"
                             :target="item.target"
                             @click="open(item, $event)"
            >
                {{ item.title }}
            </b-dropdown-item>
            <div v-if="item.divider" class="dropdown-divider" />
        </template>
    </b-nav-item-dropdown>
</template>

<script>
    import _ from "underscore";
    import { VBTooltip } from "bootstrap-vue";
    import { VBPopover } from "bootstrap-vue";

    export default {
        name: "MastheadItem",
        directives: {
            "v-b-tooltip": VBTooltip,
            "v-b-popover": VBPopover
        },
        props: {
            tab: {
                type: Object,
            },
            activeTab: {
                type: Function,
            },
            appRoot: {
                type: String,
            },
            Galaxy: {
                type: Object,
            }
        },
        computed: {
            popoverNote() {
                return `Please <a href="${this.appRoot}login">login or register</a> to use this feature.`;
            }
        },
        created() {
            if (this.tab.onbeforeunload) {
                document.addEventListener('beforeunload', () => {
                    this.tab.onbeforeunload();
                });
            }
        },
        mounted() {
            console.log(this.tab)
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
                    this.$emit('updateScratchbookTab', tab);
                    // _.each(this.tabs, (tab, i) => {
                    //     if (tab.id === "enable-scratchbook") {
                    //         tab.active = !tab.active;
                    //
                    //         this.$set(this.tabs, i, {
                    //             ...tab,
                    //             toggle: tab.active,
                    //             show_note: tab.active,
                    //             note_cls: tab.active && "fa fa-check"
                    //         });
                    //     }
                    // });
                }
            },
        },
    }
</script>

<style scoped>
    .nav-note-port {
        position: absolute;
        font-weight: 700;
        font-size: .7rem;
        color: gold;
        line-height: 3.5rem;
        margin-left: 1px;
    }

    li .nav-link > span.toggle {
        color: gold;
    }
</style>