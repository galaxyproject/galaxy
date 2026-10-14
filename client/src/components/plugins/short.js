const textLength = 80;

function setShortText(el, binding) {
    let textContent = binding.value;
    if (textContent.length > textLength) {
        textContent = `${textContent.substr(0, textLength)}...`;
    }
    el.classList.add("text-break");
    el.textContent = textContent;
}

/** Renders a string truncated to 80 characters: `v-short="text"`. */
export const vShort = {
    mounted: setShortText,
    updated: setShortText,
};
