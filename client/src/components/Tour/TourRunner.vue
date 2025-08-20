<script setup lang="ts">
import { ref } from "vue";

import { getTourData, type TourRequirements, type TourStep } from "@/api/tours";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

import Tour from "./Tour.vue";

/** Maximum number of attempts to wait for site elements */
const ATTEMPTS = 200;
/** Delay between each attempt to then click site elements */
const DELAY = 200;

const props = defineProps<{
    tourId: string;
}>();

const emit = defineEmits(["end-tour"]);

const steps = ref<TourStep[]>([]);
const requirements = ref<TourRequirements>([]);
const ready = ref(false);
const waitingOnElement = ref<string | null>(null);

async function initialize() {
    try {
        const { requirements: tourRequirements, steps: tourSteps } = await getTourData(props.tourId);

        if (!tourSteps.length) {
            throw new Error("No steps found for the tour.");
        }

        requirements.value = tourRequirements;
        steps.value = tourSteps;

        ready.value = true;
    } catch (error) {
        Toast.error(errorMessageAsString(error), "Failed to start tour");
    }
}

initialize();

/** Performs any pre-step clicking and text insertion for the provided step. */
async function onBefore(step: TourStep): Promise<void> {
    // Wait for element before continuing tour
    if (step.element) {
        await waitForElement(step.element, ATTEMPTS);
    }

    let preclick = step.preclick;
    if (preclick === true && step.element) {
        preclick = [step.element];
    }
    doClick(preclick);

    if (step.element && step.textinsert !== null && step.textinsert !== undefined) {
        doInsert(step.element, step.textinsert);
    }
}

/** Performs any post-step clicking for the provided step. */
async function onNext(step: TourStep): Promise<void> {
    let postclick = step.postclick;
    if (postclick === true && step.element) {
        postclick = [step.element];
    }
    doClick(postclick);
}

/** Returns the element for the given selector */
function getElement(selector: string) {
    if (selector) {
        try {
            return document.querySelector(selector);
        } catch (error) {
            throw Error(`Invalid selector. ${selector}`);
        }
    }
}

/** Waits for the element to be available in the DOM
 * @param selector The CSS selector of the element to wait for
 * @param tries The number of attempts to find the element before erroring _(recursive counter)_
 */
async function waitForElement(selector: string, tries: number): Promise<Element | null> {
    if (!selector) {
        waitingOnElement.value = null;
        return null;
    }

    waitingOnElement.value = selector;

    const el = getElement(selector);
    const rect = el?.getBoundingClientRect();
    const isVisible = !!(rect && rect.width > 0 && rect.height > 0);

    if (el && isVisible) {
        waitingOnElement.value = null;
        return el;
    } else if (tries > 0) {
        // Wait and try again
        await new Promise((resolve) => setTimeout(resolve, DELAY));
        return waitForElement(selector, tries - 1);
    } else {
        waitingOnElement.value = null;
        throw new Error(`Element not found. ${selector}`);
    }
}

/** Performs a click event on the selected element(s) */
function doClick(targets?: boolean | string[] | null) {
    if (targets && Array.isArray(targets)) {
        targets.forEach((selector) => {
            const el = getElement(selector);
            if (el) {
                (el as HTMLElement).click();
            } else {
                throw Error(`Click target not found. ${selector}`);
            }
        });
    }
}

/** Performs any text insertion for the given selector */
function doInsert(selector: string, value: string) {
    const el = getElement(selector);
    if (el) {
        (el as HTMLInputElement | HTMLTextAreaElement).value = value;
        const event = new Event("input");
        el.dispatchEvent(event);
    } else {
        throw Error(`Insert target not found. ${selector}`);
    }
}
</script>

<template>
    <Tour
        v-if="ready"
        :tour-id="props.tourId"
        :steps="steps"
        :requirements="requirements"
        :waiting-on-element="waitingOnElement"
        :on-before="onBefore"
        :on-next="onNext"
        @end-tour="emit('end-tour')" />
</template>
