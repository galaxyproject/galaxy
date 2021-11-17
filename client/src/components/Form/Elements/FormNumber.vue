<template>
    <b-row align-v="center">
        <b-col :sm="isSliderVisible ? defaultInputSizeWithSlider : false">
            <b-form-input v-model="currentValue" size="sm" />
        </b-col>
        <b-col class="pl-0" v-if="isSliderVisible">
            <b-form-input v-model="currentValue" :min="min" :max="max" type="range" />
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        value: {
            type: [String, Number],
            required: true,
        },
        type: {
            type: String,
            required: true,
            validator: (prop) => ["integer", "float"].includes(prop),
        },
        min: {
            type: Number,
            required: false,
            default: undefined,
        },
        max: {
            type: Number,
            required: false,
            default: undefined,
        },
    },
    data() {
        return {
            defaultInputSizeWithSlider: 4,
        };
    },
    computed: {
        isSliderVisible() {
            return this.min && this.max && this.max > this.min;
        },
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
    },
};
</script>
<style scoped>
.form-number-input {
    max-width: 3.6rem;
}
</style>
