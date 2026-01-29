<template>
    <div>
        <div class="text-field">
            <!-- edit mode -->
            <div v-if="isEditMode">
                <b-form-textarea class="form-control" :value="text" rows="3" no-resize @change="updateValue" />
            </div>
            <!-- shrink long text -->
            <div v-else-if="text && text.length > maxDescriptionLength && !isExpanded">
                <!-- eslint-disable vue/no-v-html -->
                <span
                    class="shrinked-description"
                    :title="text"
                    v-html="linkify(sanitize(text.substring(0, maxDescriptionLength)))">
                </span>
                <!-- eslint-enable vue/no-v-html -->
                <span :title="text">...</span>
                <a class="more-text-btn" href="javascript:void(0)" @click="toggleDescriptionExpand">(more) </a>
            </div>
            <!-- Regular -->
            <div v-else>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-html="linkify(sanitize(text ?? ''))"></div>
                <!-- hide toggle expand if text is too short -->
                <a
                    v-if="text && text.length > maxDescriptionLength"
                    class="more-text-btn"
                    href="javascript:void(0)"
                    @click="toggleDescriptionExpand"
                    >(less)
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import BootstrapVue from "bootstrap-vue";
import { MAX_DESCRIPTION_LENGTH } from "components/Libraries/library-utils";
import { sanitize } from "dompurify";
import linkifyHtml from "linkify-html";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    props: {
        text: {
            type: String,
            required: false,
        },
        changedValue: {
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
        };
    },
    methods: {
        sanitize,
        updateValue(value) {
            this.$emit("update:changedValue", value);
        },
        toggleDescriptionExpand() {
            this.$emit("toggleDescriptionExpand");
        },
        linkify(raw_text) {
            return linkifyHtml(raw_text);
        },
    },
};
</script>
<style scoped>
.text-field {
    min-width: 20rem;
}
</style>
