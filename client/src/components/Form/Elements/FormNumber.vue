<template>
    <div>
        <b-alert v-if="errorMessage" class="mt-2" :show="dismissCountDown" variant="info" @dismissed="resetAlert">
            {{ errorMessage }}
        </b-alert>
        <b-row align-v="center">
            <b-col :sm="isRangeValid ? defaultInputSizeWithSlider : false">
                <!-- regular dot and dot on numpad have different codes -->
                <b-form-input
                    v-model="currentValue"
                    :step="step"
                    size="sm"
                    :type="fieldType"
                    @change="onInputChange"
                    @keydown.190.capture="onFloatInput"
                    @keydown.110.capture="onFloatInput" />
            </b-col>
            <b-col v-if="isRangeValid" class="pl-0">
                <b-form-input v-model="currentValue" :min="min" :max="max" :step="step" type="range" />
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
            type: [Number, String],
            required: false,
            default: undefined,
        },
        max: {
            type: [Number, String],
            required: false,
            default: undefined,
        },
        workflowBuildingMode: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            defaultInputSizeWithSlider: 4,
            dismissSecs: 5,
            dismissCountDown: 0,
            errorMessage: "",
            fractionWarning: "This output doesn't allow fractions!",
            decimalPlaces: this.type.toLowerCase() === "integer" ? 0 : this.getNumberOfDecimals(this.value),
        };
    },
    computed: {
        currentValue: {
            get() {
                return this.value;
            },
            set(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.$emit("input", newVal);
                }
            },
        },
        fieldType() {
            return this.workflowBuildingMode ? "text" : "number";
        },
        isRangeValid() {
            return !isNaN(this.min) && !isNaN(this.max) && this.max > this.min;
        },
        isInteger() {
            return this.type.toLowerCase() === "integer";
        },
        isFloat() {
            return !this.isInteger;
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
            this.resetAlert();
            if (this.isOutOfRange(value)) {
                this.showOutOfRangeWarning(value);
                this.currentValue = value > this.max ? this.max : this.min;
            }
            if (this.isFloat) {
                this.decimalPlaces = this.getNumberOfDecimals(this.currentValue);
            }
        },
        showAlert(error) {
            if (error) {
                this.errorMessage = error;
                this.dismissCountDown = this.dismissSecs;
            }
        },
        isOutOfRange(value) {
            return this.isRangeValid && (value > this.max || value < this.min);
        },
        showOutOfRangeWarning(value) {
            const warningMessage = `${value} is out of ${this.min} - ${this.max} range!`;
            this.showAlert(warningMessage);
        },
        resetAlert() {
            this.dismissCountDown = 0;
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
    },
};
</script>
