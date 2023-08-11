<template>
    <div>
        <small>Deleted:</small>
        <GFormGroup class="m-0">
            <GFormRadioGroup v-model="deleted" :options="options" size="sm" buttons description="filter deleted" />
        </GFormGroup>
        <small>Visible:</small>
        <GFormGroup class="m-0">
            <GFormRadioGroup v-model="visible" :options="options" size="sm" buttons description="filter visible" />
        </GFormGroup>
    </div>
</template>

<script>
import { GFormGroup, GFormRadioGroup } from "@/component-library";

export default {
    components: {
        GFormGroup,
        GFormRadioGroup,
    },
    props: {
        settings: { type: Object, required: true },
    },
    data() {
        return {
            options: [
                { text: "Any", value: "any" },
                { text: "Yes", value: true },
                { text: "No", value: false },
            ],
        };
    },
    computed: {
        deleted: {
            get() {
                return this.getValue("deleted");
            },
            set(value) {
                this.onChange("deleted", value);
            },
        },
        visible: {
            get() {
                return this.getValue("visible");
            },
            set(value) {
                this.onChange("visible", value);
            },
        },
    },
    methods: {
        getValue(name) {
            const value = this.settings[`${name}:`];
            return value !== undefined ? value : "any";
        },
        onChange(name, value) {
            value = value !== null ? value : undefined;
            this.$emit("change", `${name}:`, value);
        },
    },
};
</script>
