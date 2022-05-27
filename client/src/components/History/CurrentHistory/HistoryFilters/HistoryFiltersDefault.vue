<template>
    <div>
        <small>Deleted:</small>
        <b-form-group class="m-0">
            <b-form-radio-group v-model="deleted" :options="options" size="sm" buttons description="filter deleted" />
        </b-form-group>
        <small>Visible:</small>
        <b-form-group class="m-0">
            <b-form-radio-group v-model="visible" :options="options" size="sm" buttons description="filter visible" />
        </b-form-group>
    </div>
</template>

<script>
export default {
    props: {
        settings: { type: Object, required: true },
    },
    data() {
        return {
            options: [
                { text: "Any", value: null },
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
            return value !== undefined ? value : null;
        },
        onChange(name, value) {
            value = value !== null ? value : undefined;
            this.$emit("change", `${name}:`, value);
        },
    },
};
</script>
