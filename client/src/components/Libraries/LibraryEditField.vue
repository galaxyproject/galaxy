<template>
    <div>
        <div class="text-field">
            <!-- edit mode -->
            <div v-if="isEditMode">
                <BFormTextarea class="form-control" :value="text" rows="3" no-resize @change="updateValue" />
            </div>
            <!-- shrink long text -->
            <div v-else-if="text && text.length > maxDescriptionLength && !isExpanded">
                <span
                    v-sanitize-html="linkify(text.substring(0, maxDescriptionLength))"
                    class="shrinked-description"
                    :title="text">
                </span>

                <span :title="text">...</span>
                <a class="more-text-btn" href="javascript:void(0)" @click="toggleDescriptionExpand">(more) </a>
            </div>
            <!-- Regular -->
            <div v-else>
                <div v-sanitize-html="linkify(text ?? '')"></div>

                <!-- hide toggle expand if text is too short -->
                <a
                    v-if="text && text.length > maxDescriptionLength"
                    class="more-text-btn"
                    href="javascript:void(0)"
                    @click="toggleDescriptionExpand">
                    (less)
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import { BFormTextarea } from "bootstrap-vue";
import linkifyHtml from "linkify-html";

import { MAX_DESCRIPTION_LENGTH } from "@/components/Libraries/library-utils";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

export default {
    components: {
        BFormTextarea,
    },
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
        updateValue(value) {
            this.$emit("update:changedValue", value);
        },
        toggleDescriptionExpand() {
            this.$emit("toggleDescriptionExpand");
        },
        linkify(raw_text) {
            // Clean before linkifying: linkify-html tokenizes its input as HTML, so a
            // bare "<" in plain text would otherwise be read as the start of a tag.
            return linkifyHtml(sanitizeHtml(raw_text));
        },
    },
};
</script>
<style scoped>
.text-field {
    min-width: 20rem;
}
</style>
