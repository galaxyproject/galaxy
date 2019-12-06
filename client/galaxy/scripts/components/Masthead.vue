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
                                    :active="tab.id === activeTab"
                                    :class="{
                                        active: tab.id === activeTab
                                    }"
                                    v-b-tooltip.hover.bottom
                                    :title="tab.tooltip"
                                    :style="{
                                        visibility: tab.visible ? 'visible' : 'hidden',
                                    }"
                                    :id="tab.id" href="#"

                                    :link-classes="[tab.icon && 'nav-icon', tab.icon && 'fa', tab.icon || '']"
                        >
                            {{ tab["title"] }}
                        </b-nav-item>

                        <b-nav-item-dropdown v-else
                                             :text="tab.title"
                                             v-b-tooltip.hover.bottom
                                             :title="tab.tooltip"
                                             :style="{visibility: tab.visible ? 'visible' : 'hidden'}"
                                             :id="tab.id" href="#">
                            <b-dropdown-item v-for="item in tab.menu" href="#">{{ item["title"] }}</b-dropdown-item>
                        </b-nav-item-dropdown>
                    </template>
                </b-navbar-nav>

                <div ref="quota-meter-container" class="quota-meter-container"/>
            </b-navbar>
        </div>
</template>

<script>
    import { VBTooltip } from "bootstrap-vue";
    import { BNavbar, BNavbarBrand, BNavbarNav } from "bootstrap-vue";

    export default {
        name: "Masthead",
        directives: {
            "v-b-tooltip": VBTooltip
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
            }
        },
        components: {
            BNavbar,
            BNavbarBrand,
            BNavbarNav,
        },
        mounted() {
            console.log(this.tabs);
            console.log(this.activeTab);

            this.quotaMeter.setElement(this.$refs['quota-meter-container']);
            this.quotaMeter.render();
        }
    }
</script>

<style scoped>
    i.fa {
        width: 100%;
        height: 100%;
    }

    .icon > a {

    }
</style>
