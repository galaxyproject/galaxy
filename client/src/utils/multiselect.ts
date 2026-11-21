import { nextTick } from "vue";

/** Keep keyboard navigation visible when option slots contain wrapped text. */
export async function scrollMultiselectOptionIntoView(event: KeyboardEvent) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
        return;
    }
    const selector = event.currentTarget as HTMLElement;
    await nextTick();
    const list = selector.querySelector<HTMLElement>(".multiselect__content-wrapper");
    const option = selector.querySelector<HTMLElement>(".multiselect__option--highlight");
    if (!list || !option) {
        return;
    }
    // vue-multiselect scrolls using index * optionHeight, which assumes every
    // option is the same height. Use rendered bounds for multiline guidance.
    const listBounds = list.getBoundingClientRect();
    const optionBounds = option.getBoundingClientRect();
    if (optionBounds.top < listBounds.top || optionBounds.height > listBounds.height) {
        list.scrollTop += optionBounds.top - listBounds.top;
    } else if (optionBounds.bottom > listBounds.bottom) {
        list.scrollTop += optionBounds.bottom - listBounds.bottom;
    }
}
