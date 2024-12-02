<template>
    <div class="mb-2" :data-lint-status="isOkay ? 'ok' : 'warning'">
        <div v-if="isOkay">
            <FontAwesomeIcon icon="check" class="text-success" />
            <span>{{ successMessage }}</span>
        </div>
        <div v-else>
            <FontAwesomeIcon icon="exclamation-triangle" class="text-warning" />
            <span>{{ warningMessage | localize }}</span>
            <div v-if="hasWarningItems" class="mt-2">
                <div
                    v-for="(item, idx) in warningItems"
                    :key="idx"
                    class="ml-2"
                    @focusin="onMouseOver(item)"
                    @mouseover="onMouseOver(item)"
                    @focusout="onMouseLeave(item)"
                    @mouseleave="onMouseLeave(item)">
                    <a
                        href="#"
                        class="scrolls"
                        :data-item-index="idx"
                        v-bind="dataAttributes(item)"
                        @click="onClick(item)">
                        <FontAwesomeIcon v-if="item.autofix" icon="magic" class="mr-1" />
                        <FontAwesomeIcon v-else icon="search" class="mr-1" />
                        {{ item.stepLabel }}: {{ item.warningLabel }}
                    </a>
                </div>
            </div>
            <p v-else class="mt-2 ml-2">
                <a href="#" @click="onClick"> <FontAwesomeIcon icon="pencil-alt" class="mr-1" />{{ attributeLink }} </a>
            </p>
        </div>
    </div>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faExclamationTriangle, faMagic, faPencilAlt, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { dataAttributes } from "./modules/linting";

Vue.use(BootstrapVue);

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
        dataAttributes: dataAttributes,
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
