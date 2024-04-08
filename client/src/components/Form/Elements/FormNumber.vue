<script setup lang="ts">
import { BAlert, BCol, BFormInput, BRow } from "bootstrap-vue";
import { computed, ref } from "vue";

interface Props {
    value: number;
    type: "integer" | "float";
    min?: number;
    max?: number;
    workflowBuildingMode?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    min: undefined,
    max: undefined,
});

const emit = defineEmits<{
    (e: "input", value: string | number): void;
}>();

const dismissSecs = ref(5);
const errorMessage = ref("");
const dismissCountDown = ref(0);
const defaultInputSizeWithSlider = ref(4);
const fractionWarning = ref("This output doesn't allow fractions!");

const isInteger = computed(() => {
    return props.type.toLowerCase() === "integer";
});
const fieldType = computed(() => {
    return props.workflowBuildingMode ? "text" : "number";
});
const isRangeValid = computed(() => {
    return !isNaN(props.min) && !isNaN(props.max) && props.max > props.min;
});
const decimalPlaces = computed(() => {
    return props.type.toLowerCase() === "integer" ? 0 : getNumberOfDecimals(props.value);
});
const currentValue = computed({
    get() {
        return props.value;
    },
    set(newVal: string | number) {
        if (newVal !== props.value) {
            emit("input", newVal);
        }
    },
});

/**
 * Dynamically sets the step value depending on the
 * current value precision when float number.
 */
const step = computed(() => {
    if (isInteger.value) {
        return 1;
    }

    if (decimalPlaces.value < 2) {
        return 0.1;
    } else if (decimalPlaces.value < 3) {
        return 0.01;
    }

    return 0.001;
});

function onFloatInput(e: KeyboardEvent) {
    if (isInteger.value) {
        e.preventDefault();

        showAlert(fractionWarning.value);
    }
}

function onInputChange(value: number) {
    resetAlert();

    if (isOutOfRange(value)) {
        showOutOfRangeWarning(value);

        currentValue.value = value > props.max ? props.max : props.min;
    }
}

function showAlert(error: string) {
    if (error) {
        errorMessage.value = error;
        dismissCountDown.value = dismissSecs.value;
    }
}

function isOutOfRange(value: number) {
    return isRangeValid.value && (value > props.max || value < props.min);
}

function showOutOfRangeWarning(value: number) {
    const warningMessage = `${value} is out of ${props.min} - ${props.max} range!`;

    showAlert(warningMessage);
}

function resetAlert() {
    dismissCountDown.value = 0;
}

/**
 * https://stackoverflow.com/questions/10454518/javascript-how-to-retrieve-the-number-of-decimals-of-a-string-number
 */
function getNumberOfDecimals(value: number | string): number {
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
}
</script>

<template>
    <div>
        <BAlert v-if="errorMessage" class="mt-2" :show="dismissCountDown" variant="info" @dismissed="resetAlert">
            {{ errorMessage }}
        </BAlert>

        <BRow align-v="center">
            <BCol :sm="isRangeValid ? defaultInputSizeWithSlider : false">
                <!-- regular dot and dot on numpad have different codes -->
                <BFormInput
                    v-model="currentValue"
                    class="ui-input"
                    :no-wheel="true"
                    :step="step"
                    :type="fieldType"
                    @change="onInputChange"
                    @keydown.190.capture="onFloatInput"
                    @keydown.110.capture="onFloatInput" />
            </BCol>

            <BCol v-if="isRangeValid" class="pl-0">
                <BFormInput v-model="currentValue" class="ui-input" :min="min" :max="max" :step="step" type="range" />
            </BCol>
        </BRow>
    </div>
</template>
