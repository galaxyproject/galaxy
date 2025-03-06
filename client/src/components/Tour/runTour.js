import axios from "axios";
import { getAppRoot } from "onload";
import { mountVueComponent } from "utils/mountVueComponent";

import Tour from "./Tour";

// delays and maximum number of attempts to wait for element
const attempts = 200;
const delay = 200;

// return tour data
async function getTourData(tourId) {
    const url = `${getAppRoot()}api/tours/${tourId}`;
    const { data } = await axios.get(url);
    return data;
}

// returns the selected element
function getElement(selector) {
    if (selector) {
        try {
            return document.querySelector(selector);
        } catch (error) {
            throw Error(`Invalid selector. ${selector}`);
        }
    }
}

// wait for element
function waitForElement(selector, resolve, reject, tries) {
    if (selector) {
        const el = getElement(selector);
        const rect = el?.getBoundingClientRect();
        const isVisible = !!(rect && rect.width > 0 && rect.height > 0);
        if (el && isVisible) {
            resolve();
        } else if (tries > 0) {
            setTimeout(() => {
                waitForElement(selector, resolve, reject, tries - 1);
            }, delay);
        } else {
            throw Error("Element not found.", selector);
        }
    } else {
        resolve();
    }
}

// performs a click event on the selected element
function doClick(targets) {
    if (targets) {
        targets.forEach((selector) => {
            const el = getElement(selector);
            if (el) {
                el.click();
            } else {
                throw Error("Click target not found.", selector);
            }
        });
    }
}

// insert text into the selected element
function doInsert(selector, value) {
    if (value !== null) {
        const el = getElement(selector);
        if (el) {
            el.value = value;
            const event = new Event("input");
            el.dispatchEvent(event);
        } else {
            throw Error("Insert target not found.", selector);
        }
    }
}

// mount tours to body
function mountTour(props) {
    const container = document.createElement("div");
    const body = document.querySelector("body");
    body.append(container);
    const mountFn = mountVueComponent(Tour);
    return mountFn(props, container);
}

/**
 * Runs a Tour by identifier or from provided data.
 * @param {String} Unique Tour identifier (for api request)
 * @param {Object} Tour data
 * @returns mounted instance
 */
export async function runTour(tourId, tourData = null) {
    if (!tourData) {
        tourData = await getTourData(tourId);
    }
    const steps = [];
    Object.values(tourData.steps).forEach((step) => {
        steps.push({
            element: step.element,
            title: step.title,
            content: step.content,
            onBefore: async () => {
                return new Promise((resolve, reject) => {
                    // wait for element before continuing tour
                    waitForElement(step.element, resolve, reject, attempts);
                }).then(() => {
                    // pre-actions
                    let preclick = step.preclick;
                    if (preclick === true) {
                        preclick = [step.element];
                    }
                    doClick(preclick);
                    doInsert(step.element, step.textinsert);
                });
            },
            onNext: () => {
                // post-actions
                let postclick = step.postclick;
                if (postclick === true) {
                    postclick = [step.element];
                }
                doClick(postclick);
            },
        });
    });
    const requirements = tourData.requirements || [];
    return mountTour({ steps, requirements });
}
