<template>
    <div class="mb-2">
        <div v-if="isOkay">
            <font-awesome-icon icon="check" class="text-success" />
            <span>{{ successMessage }}</span>
        </div>
        <div v-else>
            <font-awesome-icon icon="exclamation-triangle" class="text-warning" />
            <span>{{ warningMessage | localize }}</span>
            <div v-if="hasWarningItems" class="mt-2">
                <div
                    v-for="(item, idx) in warningItems"
                    :key="idx"
                    class="ml-2"
                    @mouseover="onMouseOver(item)"
                    @mouseleave="onMouseLeave(item)">
                    <a href="#" class="scrolls" @click="onClick(item)">
                        <font-awesome-icon v-if="item.autofix" icon="magic" class="mr-1" />
                        <font-awesome-icon v-else icon="search" class="mr-1" />
                        {{ item.stepLabel }}: {{ item.warningLabel }}
                    </a>
                </div>
            </div>
            <p v-else class="mt-2 ml-2">
                <a href="#" @click="onClick">
                    <font-awesome-icon icon="pencil-alt" class="mr-1" />{{ attributeLink }}
                </a>
            </p>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
Vue.use(BootstrapVue);

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faExclamationTriangle, faMagic, faPencilAlt, faSearch } from "@fortawesome/free-solid-svg-icons";

library.add(faMagic);
library.add(faSearch);
library.add(faPencilAlt);
library.add(faCheck);
library.add(faExclamationTriangle);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        okay: {
            type: Boolean,
            default: true,
        },
        attributeLink: {
            type: String,
            default: "Edit Workflow Attributes",
        },
        successMessage: {
            type: String,
            required: true,
        },
        warningMessage: {
            type: String,
            required: true,
        },
        warningItems: {
            type: Array,
            default: null,
        },
    },
    computed: {
        isOkay() {
            return this.okay && !this.hasWarningItems;
        },
        hasWarningItems() {
            return this.warningItems && this.warningItems.length > 0;
        },
    },
    methods: {
        onMouseOver(id) {
            this.$emit("onMouseOver", id);
        },
        onMouseLeave(id) {
            this.$emit("onMouseLeave", id);
        },
        onClick(id, item) {
            this.$emit("onClick", id, item);
        },
    },
};
</script>
