export function generateId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

export function scrollToBottom(container: HTMLElement | undefined): void {
    if (container) {
        container.scrollTo({
            top: container.scrollHeight,
            behavior: "auto",
        });
    }
}
