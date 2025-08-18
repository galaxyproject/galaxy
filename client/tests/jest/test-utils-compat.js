/**
 * Vue Test Utils compatibility helpers for Vue 3
 */

/**
 * Set value on form inputs with Vue 3 compatibility
 * Handles radio buttons and checkboxes differently than regular inputs
 */
export async function setValueCompat(wrapper, value) {
    const element = wrapper.element;
    
    if (element.type === 'radio') {
        // For radio buttons, set checked and trigger change
        if (value === true || value === element.value) {
            element.checked = true;
            await wrapper.trigger('change');
        }
    } else if (element.type === 'checkbox') {
        // For checkboxes, set checked state
        element.checked = value;
        await wrapper.trigger('change');
    } else {
        // For regular inputs, use normal setValue
        await wrapper.setValue(value);
    }
}

/**
 * Helper to find and set value on a form input
 */
export async function findAndSetValue(wrapper, selector, value) {
    const input = wrapper.find(selector);
    if (input.exists()) {
        await setValueCompat(input, value);
    }
}