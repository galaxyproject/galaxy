export function selectAllText(element: HTMLElement) {
    element.focus();

    if (element instanceof HTMLTextAreaElement) {
        element.select();
    } else {
        const range = document.createRange();
        range.selectNodeContents(element);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
        deselectOnClick();
    }
}

function deselectOnClick() {
    const listener = () => {
        window.getSelection()?.removeAllRanges();
        window.removeEventListener("click", listener, { capture: true });
    };

    window.addEventListener("click", listener, { capture: true });
}
