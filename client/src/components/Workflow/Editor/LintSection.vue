<template>
    <div class="lint-section">
        <b-button
            :aria-expanded="expanded ? 'true' : 'false'"
            :aria-controls="collapseId"
            :variant="variant"
            @click="expanded = !expanded"
        >
            <font-awesome-icon icon="check" v-if="okay" />
            <font-awesome-icon icon="times" v-else />
            {{ title }}
            <font-awesome-icon icon="angle-double-up" v-if="expanded" />
            <font-awesome-icon icon="angle-double-down" v-else />
        </b-button>
        <b-collapse :id="collapseId" v-model="expanded">
            <div class="lint-section-body">
                <slot> </slot>
            </div>
        </b-collapse>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
Vue.use(BootstrapVue);

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faTimes, faAngleDoubleDown, faAngleDoubleUp } from "@fortawesome/free-solid-svg-icons";

library.add(faTimes);
library.add(faCheck);
library.add(faAngleDoubleDown);
library.add(faAngleDoubleUp);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        okay: {
            type: Boolean,
        },
        title: {
            type: String,
        },
        collapseId: {
            type: String,
        },
    },
    data() {
        return {
            expanded: !this.okay,
        };
    },
    watch: {
        okay(newOkay) {
            this.expanded = !newOkay;
        },
    },
    computed: {
        variant() {
            // maybe outline- versions? They don't seem to work well with Galaxy styles?
            return this.okay ? "success" : "warning";
        },
    },
};
</script>

<style scoped>
.lint-section {
    margin: 5px;
}

/* I want something like a card maybe? but it takes up too much width? Help me Sam? */
.lint-section-body {
    padding-left: 5px;
    padding-top: 5px;
    border-left: 1px solid lightgray;
}
</style>
