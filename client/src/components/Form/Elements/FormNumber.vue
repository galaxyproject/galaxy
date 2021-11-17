<template>
    <div>
        <b-row align-v="center">
            <b-col :sm="isSliderVisible ? defaultInputSizeWithSlider : false">
                <b-form-input
                    @keydown="onInput"
                    @keydown.190.capture="onFloatInput"
                    v-model="currentValue"
                    size="sm"
                    type="number"
                />
            </b-col>
            <b-col class="pl-0" v-if="isSliderVisible">
                <b-form-input v-model="currentValue" :min="min" :max="max" type="range" />
            </b-col>
        </b-row>
        <b-alert
            class="mt-2"
            v-if="errorMessage"
            :show="dismissCountDown"
            dismissible
            variant="danger"
            @dismissed="dismissCountDown = 0"
        >
            {{ errorMessage }}
        </b-alert>
    </div>
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
            dismissSecs: 5,
            dismissCountDown: 0,
            errorMessage: "",
            fractionWarning: "This output doesn't allow fractions!",
            // currentValue: this.value,
        };
    },
    computed: {
        isSliderVisible() {
            return this.min && this.max && this.max > this.min;
        },
        isInteger() {
            return this.type === "integer";
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
    methods: {
        onFloatInput(e) {
            if (this.isInteger) {
                e.preventDefault();
                this.showAlert(this.fractionWarning);
            }
        },
        onInput(e) {
            // hide error msg on any input
            this.dismissCountDown = 0;
            // the solution far from ideal, any suggestions here would be highly appreciated
            const value = Number("" + this.currentValue + e.key);
            if (this.max && this.min && (value > this.max || value < this.min)) {
                e.preventDefault();
                const errorMessage = this.getOutOfRangeWarning(value);
                this.showAlert(errorMessage);
            }
        },
        showAlert(error) {
            if (error) {
                this.errorMessage = error;
                this.dismissCountDown = this.dismissSecs;
            }
        },
        getOutOfRangeWarning(value) {
            return `${value} is out of ${this.min} - ${this.max} range!`;
        },
    },
};
</script>
