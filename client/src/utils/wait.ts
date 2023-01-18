export function wait(milliseconds: number) {
    return new Promise<void>((resolve) => {
        setTimeout(() => resolve(), milliseconds);
    });
}
