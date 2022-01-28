<template>
    <div>
        <b-alert
            class="mt-2"
            v-if="errorMessage"
            :show="dismissCountDown"
            variant="info"
            @dismissed="dismissCountDown = 0">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col :sm="isRangeValid ? defaultInputSizeWithSlider : false">
                <!-- regular dot and dot on numpad have different codes -->
                <b-form-input
                    @change="onInputChange"
                    @keydown.190.capture="onFloatInput"
                    @keydown.110.capture="onFloatInput"
                    v-model="currentValue"
                    :step="step"
                    size="sm"
                    type="number" />
            </b-col>
            <b-col class="pl-0" v-if="isRangeValid">
                <b-form-input
                    v-model="currentValue"
                    :min="min"
                    :max="max"
                    :step="step"
                    type="range"
                    @change="notifyValueChange" />
            </b-col>
        </b-row>
    </div>
</template>

<script>
export default {
    props: {
        value: {
            required: true,
        },
        type: {
            type: String,
            required: true,
            validator: (prop) => ["integer", "float"].includes(prop.toLowerCase()),
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
            currentValue: this.value,
            decimalPlaces: this.isInteger ? 0 : this.getNumberOfDecimals(this.value),
        };
    },
    computed: {
        isRangeValid() {
            return !isNaN(this.min) && !isNaN(this.max) && this.max > this.min;
        },
        isInteger() {
            return this.type.toLowerCase() === "integer";
        },
        /**
         * Dynamically sets the step value depending on the
         * current value precision when float number.
         */
        step() {
            if (this.isInteger) {
                return 1;
            }
            const numDecimals = this.decimalPlaces;
            if (numDecimals < 2) {
                return 0.1;
            }
            if (numDecimals < 3) {
                return 0.01;
            }
            return 0.001;
        },
    },
    methods: {
        onFloatInput(e) {
            if (this.isInteger) {
                e.preventDefault();
                this.showAlert(this.fractionWarning);
            }
        },
        onInputChange(value) {
            // hide error message after value has changed
            this.dismissCountDown = 0;
            if (this.isRangeValid && (value > this.max || value < this.min)) {
                const errorMessage = this.getOutOfRangeWarning(value);
                this.currentValue = value > this.max ? this.max : this.min;
                this.showAlert(errorMessage);
            }
            if (!this.isInteger) {
                this.decimalPlaces = this.getNumberOfDecimals(this.currentValue);
            }
            this.notifyValueChange();
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
        /**
         * https://stackoverflow.com/questions/10454518/javascript-how-to-retrieve-the-number-of-decimals-of-a-string-number
         */
        getNumberOfDecimals(value) {
            if (value == null) {
                return 0;
            }
            var match = value.toString().match(/(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/);
            if (!match) {
                return 0;
            }
            return Math.max(
                0,
                // Number of digits right of decimal point.
                (match[1] ? match[1].length : 0) -
                    // Adjust for scientific notation.
                    (match[2] ? +match[2] : 0)
            );
        },
        notifyValueChange() {
            this.$emit("input", this.currentValue);
        },
    },
};
</script>
