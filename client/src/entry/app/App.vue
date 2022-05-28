<template>
    <body scroll="no" class="full-content">
        <div id="everything">
            <div id="background"/>
            <Masthead
                id="masthead"
                :mastheadState="getState()"
                :displayGalaxyBrand="options.display_galaxy_brand"
                :brand="options.brand"
                :brandLink="staticUrlToPrefixed(options.logo_url)"
                :brandImage="staticUrlToPrefixed(options.logo_src)"
                :brandImageSecondary="staticUrlToPrefixed(options.logo_src_secondary)"
                :menuOptions="options"/>
            <small id="messagebox"/>
            <small id="inactivebox" class="alert rounded-0 m-0 p-2 alert-warning" />
            <div id="columns">
                <div id="left" class="unified-panel"/>
                <div id="center" />
                <div id="right" class="unified-panel" />
            </div>
        </div>
        <div id="dd-helper" />
    </body>
</template>
<script>
import { MastheadState } from "layout/masthead";
import Masthead from "components/Masthead/Masthead.vue";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload";

export default {
    components: {
        Masthead,
    },
    computed: {
        options() {
            return getGalaxyInstance().config;
        },
    },
    methods: {
        getState() {
            return new MastheadState();
        },
        staticUrlToPrefixed(url) {
            return url?.startsWith("/") ? `${getAppRoot()}${url.substring(1)}` : url;
        },
    },
}
</script>