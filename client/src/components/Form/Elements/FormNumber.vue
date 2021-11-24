<template>
    <div>
        <b-row align-v="center">
            <b-col :sm="isRangeValid ? defaultInputSizeWithSlider : false">
                <!-- regular dot and dot on numpad have different codes -->
                <b-form-input
                    @change="onInputChange"
                    @keydown.190.capture="onFloatInput"
                    @keydown.110.capture="onFloatInput"
                    v-model="currentValue"
                    size="sm"
                    type="number"
                />
            </b-col>
            <b-col class="pl-0" v-if="isRangeValid">
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
        };
    },
    computed: {
        isRangeValid() {
            return !isNaN(this.min) && !isNaN(this.max) && this.max > this.min;
        },
        isInteger() {
            return this.type.toLowerCase() === "integer";
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
            this.$emit("input", this.currentValue);
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
