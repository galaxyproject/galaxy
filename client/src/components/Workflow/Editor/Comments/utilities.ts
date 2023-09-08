export function selectAllText(element: HTMLElement) {
    element.focus();

    if (element instanceof HTMLTextAreaElement) {
        element.select();
    } else {
        const range = document.createRange();
        range.selectNodeContents(element);
        window.getSelection()?.removeAllRanges();
        window.getSelection()?.addRange(range);
    }
}
