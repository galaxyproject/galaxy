<template>
    <div id="masthead"></div>
</template>

<script>
import { getGalaxyInstance } from "app";
import Masthead from "layout/masthead";

export default {
    mounted() {
        this.backboneRender();
    },

    updated() {
        this.backboneRender();
    },

    methods: {
        backboneRender() {
            // dont bother unless we're in top window
            if (window.top !== window) {
                return;
            }

            let galaxy = getGalaxyInstance();

            // old backbone view
            if (!galaxy.masthead) {
                galaxy.masthead = new Masthead.View(this.$props);
            }

            // bolt the rendered DOM onto the vue component's element
            let backboneDom = galaxy.masthead.render();
            this.$el.appendChild(backboneDom.$el[0]);
        }
    }
};
</script>

<style lang="scss">
#masthead:empty {
    display: none;
}

.framed {
    #messagebox,
    #masthead {
        display: none;
    }

    #center,
    #right,
    #left {
        top: 0;
    }
}
</style>
