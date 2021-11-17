<template>
    <div>
        <b-row align-v="center">
            <b-col :sm="isSliderVisible ? defaultInputSizeWithSlider : false">
                <b-form-input @keydown.190.capture="onFloatInput" :value="value" size="sm" type="number" />
            </b-col>
            <b-col class="pl-0" v-if="isSliderVisible">
                <b-form-input :value="value" :min="min" :max="max" type="range" />
            </b-col>
        </b-row>
        <b-alert
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
                let value = val;
                if (this.type === "integer") {
                    value = Math.round(value);
                }
                this.$emit("input", value);
            },
        },
    },
    methods: {
        onInput(e) {
            console.log(e);
        },
        onFloatInput(e) {
            console.log(e);
            if (this.isInteger) {
                e.preventDefault();
                this.errorMessage = this.fractionWarning;
                this.showAlert();
            }
        },
        showAlert() {
            this.dismissCountDown = this.dismissSecs;
        },
    },
};
</script>
