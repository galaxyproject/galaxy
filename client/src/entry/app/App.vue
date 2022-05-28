<template>
    <div>
        <div id="everything">
            <div id="background"/>
            <div id="masthead">
                <Masthead
                    :mastheadState="getState()"
                    :displayGalaxyBrand="options.display_galaxy_brand"
                    :brand="options.brand"
                    :brandLink="staticUrlToPrefixed(options.logo_url)"
                    :brandImage="staticUrlToPrefixed(options.logo_src)"
                    :brandImageSecondary="staticUrlToPrefixed(options.logo_src_secondary)"
                    :menuOptions="options"/>
            </div>
            <small id="messagebox"/>
            <small id="inactivebox" class="alert rounded-0 m-0 p-2 alert-warning" />
            <div id="columns">
                <div id="left" class="unified-panel"/>
                <div id="center" />
                <div id="right" class="unified-panel" />
            </div>
        </div>
        <div id="dd-helper" />
    </div>
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