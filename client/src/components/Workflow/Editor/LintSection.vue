<template>
    <div class="mb-2" :data-lint-status="isOkay ? 'ok' : 'warning'">
        <div v-if="isOkay">
            <FontAwesomeIcon :icon="faCheck" class="text-success" />
            <span>{{ successMessage }}</span>
        </div>
        <div v-else>
            <FontAwesomeIcon :icon="faExclamationTriangle" class="text-warning" />
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
                        <FontAwesomeIcon v-if="item.autofix" :icon="faMagic" class="mr-1" />
                        <FontAwesomeIcon v-else :icon="faSearch" class="mr-1" />
                        {{ item.stepLabel }}: {{ item.warningLabel }}
                    </a>
                </div>
            </div>
            <p v-else class="mt-2 ml-2">
                <a href="#" @click="onClick">
                    <FontAwesomeIcon :icon="faPencilAlt" class="mr-1" />{{ attributeLink }}
                </a>
            </p>
        </div>
    </div>
</template>

<script>
import { faCheck, faExclamationTriangle, faMagic, faPencilAlt, faSearch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import { dataAttributes } from "./modules/linting";

Vue.use(BootstrapVue);

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
    data() {
        return {
            faCheck,
            faExclamationTriangle,
            faMagic,
            faPencilAlt,
            faSearch,
        };
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
