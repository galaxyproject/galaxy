<template>
    <div>
        <BFormCheckbox v-model="currentStatus" class="ui-switch" switch>
            Set value for this optional select field?
        </BFormCheckbox>
        <label v-if="currentStatus && !id" :for="inputId" class="sr-only">Optional value</label>
        <FormText
            v-if="currentStatus"
            :id="inputId"
            v-model="currentValue"
            :readonly="readonly"
            :value="value"
            :area="area"
            :placeholder="placeholder"
            :multiple="multiple"
            :datalist="datalist"
            :type="type" />
    </div>
</template>

<script>
import { BFormCheckbox } from "bootstrap-vue";

import { uid } from "@/utils/utils";

import FormText from "./FormText.vue";

export default {
    components: {
        BFormCheckbox,
        FormText,
    },
    props: {
        value: {
            default: "",
        },
        id: {
            type: String,
            default: null,
        },
        type: {
            type: String,
            default: "text",
        },
        area: {
            // <textarea> instead of <input> element
            type: Boolean,
            default: false,
        },
        multiple: {
            // Allow multiple entries to be created
            type: Boolean,
            default: false,
        },
        readonly: {
            type: Boolean,
            default: false,
        },
        placeholder: {
            type: String,
            default: null,
        },
        datalist: {
            // Display list of suggestions in autocomplete dialog
            type: Array,
            default: null,
        },
    },
    emits: ["input"],
    data() {
        return {
            status: false,
            generatedId: `optional-text-${uid()}`,
        };
    },
    computed: {
        inputId() {
            return this.id || this.generatedId;
        },
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
        currentStatus: {
            get() {
                return this.status || this.value !== null;
            },
            set(val) {
                this.status = Boolean(val);
                if (this.status) {
                    this.currentValue = "";
                } else {
                    this.currentValue = null;
                }
            },
        },
    },
};
</script>
