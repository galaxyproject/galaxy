<template>
    <div>
        <b-alert
            v-if="errorMessage"
            class="mt-2"
            :show="dismissCountDown"
            variant="info"
            dismissible
            @dismissed="resetAlert"
            @dismiss-count-down="($event) => (dismissCountDown = $event)">
            {{ errorMessage }}
            <b-progress :max="dismissSecs" :value="dismissCountDown" height="4px" class="mt-1">
                <b-progress-bar :value="dismissCountDown" variant="info" />
            </b-progress>
        </b-alert>
        <b-row align-v="center">
            <b-col :sm="isRangeValid ? defaultInputSizeWithSlider : false">
                <!-- regular dot and dot on numpad have different codes -->
                <b-form-input
                    v-model="currentValue"
                    class="ui-input"
                    :no-wheel="true"
                    :step="step"
                    :type="fieldType"
                    @change="onInputChange"
                    @keypress="isNumberOrDecimal"
                    @keydown.190.capture="onFloatInput"
                    @keydown.110.capture="onFloatInput" />
            </b-col>
            <b-col v-if="isRangeValid" class="pl-0">
                <b-form-input v-model="currentValue" class="ui-input" :min="min" :max="max" :step="step" type="range" />
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
            validator: (prop) => typeof prop == "number" || prop === null,
        },
        max: {
            type: [Number, String],
            required: false,
            default: undefined,
            validator: (prop) => typeof prop == "number" || prop === null,
        },
        workflowBuildingMode: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            defaultInputSizeWithSlider: 4,
            dismissSecs: 4,
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
            return typeof this.min == "number" && typeof this.max == "number" && this.max > this.min;
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
        isNumberOrDecimal(event) {
            // NOTE: Should we check for `fieldType` here?
            const charCode = event.charCode;
            if ((charCode >= 48 && charCode <= 57) || charCode === 46) {
                return true;
            }
            event.preventDefault();
            return false;
        },
        isOutOfRange(value) {
            /* If value=null, then value is within range. */
            return (
                (typeof this.max == "number" && value > this.max) || (typeof this.min == "number" && value < this.min)
            );
        },
        showOutOfRangeWarning(value) {
            const rangeDetail =
                typeof this.max == "number" && value > this.max ? `${value} > ${this.max}` : `${value} < ${this.min}`;
            const warningMessage = `${value} is out of range! (${rangeDetail})`;
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
