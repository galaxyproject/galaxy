export function getNewAttachNode() {
    const attachElement = document.createElement("div");
    if (document.body) {
        document.body.appendChild(attachElement);
    }
    return attachElement;
}
