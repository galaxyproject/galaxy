<template>
    <div class="mb-2">
        <div v-if="noWarningItems">
            <font-awesome-icon icon="check" class="text-success" />
            <span>{{ successMessage }}</span>
        </div>
        <div v-else>
            <font-awesome-icon icon="exclamation-triangle" class="text-warning" />
            <span>{{ warningMessage }}</span>
            <ul class="mt-2">
                <li
                    v-for="(input, idx) in warningItems"
                    :key="idx"
                    @mouseover="onMouseOver(input.stepId)"
                    @mouseleave="onMouseLeave(input.stepId)"
                    class="ml-2"
                >
                    <a href="#" @click="onClick(input.stepId)" class="scrolls">
                        <i :class="input.stepIconClass" />{{ input.stepLabel }}: {{ input.inputLabel }}
                    </a>
                </li>
            </ul>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
Vue.use(BootstrapVue);

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

library.add(faCheck);
library.add(faExclamationTriangle);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        okay: {
            type: Boolean,
        },
        successMessage: {
            type: String,
            default: "",
        },
        warningMessage: {
            type: String,
            default: "",
        },
        warningItems: {
            type: Array,
            required: true,
        },
    },
    computed: {
        noWarningItems() {
            return !this.warningItems || this.warningItems.length == 0;
        },
    },
    methods: {
        onMouseOver(id) {
            this.$emit("onMouseOver", id);
        },
        onMouseLeave(id) {
            this.$emit("onMouseLeave", id);
        },
        onClick(id) {
            this.$emit("onClick", id);
        },
    },
};
</script>