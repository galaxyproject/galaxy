<template>
    <div>
        <div class="description-field">
            <!-- edit mode -->
            <div v-if="isEditMode">
                <textarea class="form-control" v-model="textField" rows="3" />
            </div>
            <!-- shrink long text -->
            <div v-else-if="text.length > maxDescriptionLength && !isExpanded">
                <span
                    class="shrinked-description"
                    :title="text"
                    v-html="linkify(text.substring(0, maxDescriptionLength))"
                >
                </span>
                <span :title="text">...</span>
                <a class="more-text-btn" @click="toggleDescriptionExpand" href="javascript:void(0)">(more) </a>
            </div>
            <!-- Regular -->
            <div v-else>
                <div v-html="linkify(text)"></div>
                <!-- hide toggle expand if text is too short -->
                <a
                    v-if="text.length > maxDescriptionLength"
                    class="more-text-btn"
                    @click="toggleDescriptionExpand"
                    href="javascript:void(0)"
                    >(less)
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import { MAX_DESCRIPTION_LENGTH } from "components/Libraries/library-utils";
import BootstrapVue from "bootstrap-vue";
import Vue from "vue";

import linkify from "linkifyjs/html";
Vue.use(BootstrapVue);

export default {
    props: {
        text: {
            type: String,
        },
        isEditMode: {
            type: Boolean,
        },
        isExpanded: {
            type: Boolean,
        },
    },
    data() {
        return {
            maxDescriptionLength: MAX_DESCRIPTION_LENGTH,
            textField: this.text,
        };
    },
    methods: {
        toggleDescriptionExpand() {
            this.$emit("toggleDescriptionExpand")
        },
        linkify(raw_text) {
            return linkify(raw_text);
        },
    },
};
</script>
