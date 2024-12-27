<script setup lang="ts">
import { faCheck, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardBody, BCardTitle } from "bootstrap-vue";
import { computed } from "vue";

import type { WizardReturnType, WizardStep } from "./useWizard";

interface Props {
    /**
     * The wizard stepper object.
     *
     * **Must be created using the `useWizard` composable.**
     */
    use?: WizardReturnType;

    /**
     * The title of the wizard.
     *
     * @default "Generic Wizard"
     */
    title?: string;

    /**
     * The label for the submit button.
     *
     * @default "Submit"
     */
    submitButtonLabel?: string;

    /**
     * Whether the wizard is busy.
     *
     * When the wizard is busy, the navigation buttons are disabled and
     * a spinner is shown on the current step.
     *
     * @default false
     */
    isBusy?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    use: undefined,
    title: undefined,
    submitButtonLabel: "Submit",
    isBusy: false,
});

function dynamicIsLast() {
    if (props.use.isLast.value) {
        return true;
    }

    let nextStepIndex = props.use.index.value + 1;
    let nextStepName = props.use.stepNames.value.at(nextStepIndex);

    while (nextStepName && props.use.steps.value[nextStepName]?.isSkippable()) {
        nextStepIndex++;
        nextStepName = props.use.stepNames.value.at(nextStepIndex);
    }

    return !nextStepName;
}

const emit = defineEmits(["submit"]);

function goNext() {
    if (props.use.current.value.isValid()) {
        if (dynamicIsLast()) {
            emit("submit");
        }

        let nextStepIndex = props.use.index.value + 1;
        let nextStepName = props.use.stepNames.value.at(nextStepIndex);

        while (nextStepName && props.use.steps.value[nextStepName]?.isSkippable()) {
            nextStepIndex++;
            nextStepName = props.use.stepNames.value.at(nextStepIndex);
        }

        if (nextStepName) {
            props.use.goTo(nextStepName);
        }
    }
}

function goBack() {
    let previousStepIndex = props.use.index.value - 1;
    let previousStepName = props.use.stepNames.value.at(previousStepIndex);

    while (previousStepName && props.use.steps.value[previousStepName]?.isSkippable()) {
        previousStepIndex--;
        previousStepName = props.use.stepNames.value.at(previousStepIndex);
    }

    if (previousStepName) {
        props.use.goTo(previousStepName);
    }
}

function determineDisplayStepIndex(index: number): number {
    const steps = Array.from(Object.values(props.use.steps.value));
    return steps.slice(0, index).filter((step) => !(step as WizardStep).isSkippable()).length + 1;
}

function allStepsBeforeAreValid(index: number): boolean {
    const steps = Array.from(Object.values(props.use.steps.value));
    return steps.slice(0, index).every((step) => (step as WizardStep).isValid() || (step as WizardStep).isSkippable());
}

function isStepDone(currentIndex: number): boolean {
    return currentIndex < props.use.index.value;
}

/**
 * This is a workaround to make the grid columns template dynamic based on the number of visible steps.
 */
const stepsGridColumnsTemplate = computed(() => {
    const numVisibleSteps = Array.from(Object.values(props.use.steps.value)).filter(
        (step) => !(step as WizardStep).isSkippable()
    ).length;
    return (
        Array(numVisibleSteps - 1)
            .fill("auto")
            .join(" ") + " max-content"
    );
});
</script>

<template>
    <BCard class="wizard-container">
        <BCardTitle v-if="title">
            <h2>{{ title }}</h2>
        </BCardTitle>
        <BCardBody v-if="props.use?.steps?.value" class="wizard">
            <BCard>
                <BCardBody class="wizard-steps">
                    <div
                        v-for="(step, id, i) in props.use.steps.value"
                        :key="id"
                        class="wizard-step"
                        :class="step.isSkippable() ? 'skipped ' : ''">
                        <button
                            class="step-number"
                            :class="{ active: props.use.isCurrent(id), done: isStepDone(i) }"
                            :disabled="(!allStepsBeforeAreValid(i) && props.use.isBefore(id)) || isBusy"
                            @click="props.use.goTo(id)">
                            <FontAwesomeIcon v-if="isStepDone(i)" :icon="faCheck" />
                            <FontAwesomeIcon v-else-if="dynamicIsLast() && isBusy" :icon="faSpinner" spin />
                            <span v-else>{{ determineDisplayStepIndex(i) }}</span>
                        </button>
                        <div class="step-label" v-text="step.label" />
                        <div class="step-line" :class="{ fill: props.use.isAfter(id) }"></div>
                    </div>
                </BCardBody>
            </BCard>

            <div class="step-content">
                <span class="h-md step-instructions" v-text="props.use.current.value.instructions" />

                <div class="step-body">
                    <slot>
                        <p>
                            Missing body for step <b>{{ props.use.current.value.label }}</b>
                        </p>
                    </slot>
                </div>
            </div>
            <div class="wizard-actions">
                <button v-if="!props.use.isFirst.value" class="go-back-btn" :disabled="isBusy" @click="goBack">
                    Back
                </button>

                <button
                    class="go-next-btn"
                    :disabled="!props.use.current.value.isValid() || isBusy"
                    :class="dynamicIsLast() ? 'btn-primary' : ''"
                    @click="goNext">
                    {{ dynamicIsLast() ? submitButtonLabel : "Next" }}
                </button>
            </div>
        </BCardBody>
    </BCard>
</template>

<style lang="scss">
@import "theme/blue.scss";

.wizard {
    padding: 0;

    .wizard-steps {
        padding: 0;
        margin: 0;
        display: grid;
        grid-auto-flow: column;
        grid-template-columns: v-bind(stepsGridColumnsTemplate);
    }

    .wizard-step {
        padding: 0;
        margin: 0;
        display: grid;
        grid-template-columns: 50px max-content auto;
        grid-template-rows: auto;
        grid-template-areas: "number label line";
        justify-items: center;

        .step-number {
            border-radius: 50%;
            width: 40px;
            height: 40px;
            background-color: $brand-secondary;
            justify-content: center;
            align-items: center;
            font-size: 1rem;
            grid-area: number;

            &.active {
                background-color: $brand-primary;
                color: white;
            }

            &.done {
                background-color: $brand-success;
                color: white;
            }
        }

        .step-label {
            align-self: center;
            grid-area: label;
            text-align: center;
            text-wrap: nowrap;
        }

        .step-line {
            margin-left: 5px;
            align-self: center;
            grid-area: line;
            width: 0;
            height: 4px;
            background-color: $brand-primary;

            &.fill {
                width: 100%;
                transform-origin: left;
                transition: width 0.2s;
            }
        }

        &.skipped {
            display: none;
        }

        &:last-child {
            justify-self: end;
        }
    }

    .step-content {
        padding: 1rem 1rem 0rem 1rem;
        display: flex;
        flex-direction: column;
        align-items: center;

        .step-instructions {
            margin-top: 0rem;
            margin-bottom: 1rem;
        }

        .step-body {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
    }

    .wizard-actions {
        padding: 1rem 1rem 0rem 1rem;

        .go-back-btn {
            float: left;
        }

        .go-next-btn {
            float: right;
        }
    }

    .wizard-selection-card {
        border-width: 3px;
        text-align: center;

        .card-header {
            border-radius: 0;
        }
    }
}
</style>
