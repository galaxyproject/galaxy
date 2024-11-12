import type { MaybeRef } from "@vueuse/core";
import { useStepper } from "@vueuse/core";

/**
 * Represents a step in a wizard.
 */
export interface WizardStep {
    /**
     * The label of the step. It will be displayed in the wizard navigation.
     */
    label: MaybeRef<string>;

    /**
     * The instructions for the step. It will be displayed in the wizard content.
     */
    instructions: MaybeRef<string>;

    /**
     * Whether the step is valid and can be completed.
     */
    isValid: () => boolean;

    /**
     * Whether the step should be skipped.
     * This is useful for optional or conditional steps.
     */
    isSkippable: () => boolean;
}

/**
 * Composable for creating a wizard with multiple steps.
 *
 * This is a thin wrapper around `useStepper` that provides a more specific type.
 * @param steps The steps of the wizard.
 * @param initialStep The initial step to start the wizard on.
 * @returns A stepper object for the wizard.
 */
export function useWizard<T extends Record<string, WizardStep>>(steps: MaybeRef<T>, initialStep?: keyof T) {
    return useStepper(steps, initialStep);
}

export type WizardReturnType = ReturnType<typeof useWizard>;
