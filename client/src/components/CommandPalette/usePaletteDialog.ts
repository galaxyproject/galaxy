import { nextTick, onBeforeUnmount, type Ref, ref } from "vue";

import type { EscapeResult } from "./usePaletteMachine";

/** Safety net for environments that never fire `transitionend` (jsdom, backgrounded tabs) */
const CLOSE_TRANSITION_FALLBACK = 200;

interface PaletteDialogOptions {
    dialogElement: Ref<HTMLDialogElement | null>;
    inputElement: Ref<HTMLInputElement | null>;
    /** The scrolling result list, whose own scrollbar keeps its mousedown default */
    resultsElement: Ref<HTMLElement | null>;
    isPaletteOpen: Readonly<Ref<boolean>>;
    closePalette: () => void;
    /** The palette's stepwise escape, also answering the dialog's own close request */
    handleEscape: () => EscapeResult;
}

/** The palette's always-mounted `<dialog>`: DOM handlers and the class-toggled open/close transition */
export function usePaletteDialog(options: PaletteDialogOptions) {
    const { dialogElement, inputElement, resultsElement, isPaletteOpen, closePalette, handleEscape } = options;

    /** Drives the enter/leave transition; the dialog element itself stays mounted */
    const paletteVisible = ref(false);
    /** Bumped by every open and close so a rapid toggle cancels the transition in flight */
    let transitionEpoch = 0;
    /** Disarms the close that is still waiting for its fade-out, if there is one */
    let cancelPendingClose: (() => void) | null = null;

    /**
     * Pressing anywhere but a control keeps the caret in the input: a border, the
     * footer, a section title or the gap between two rows would otherwise take the
     * focus and leave the palette unusable by keyboard. Only the mousedown default
     * is dropped, so the click still lands — a row is still picked, a chip still
     * applies, the backdrop still closes — and selecting the typed text is untouched.
     */
    function onDialogMousedown(event: MouseEvent) {
        const target = event.target as HTMLElement | null;
        if (!target || target.closest("input, button")) {
            return;
        }
        // Firefox drives a scrollbar drag off the same default, so a press on the
        // result list's own scrollbar track is left to the browser
        if (target === resultsElement.value && event.offsetX >= target.clientWidth) {
            return;
        }
        event.preventDefault();
    }

    function onClickDialog(event: MouseEvent) {
        if ((event.target as HTMLElement | null)?.tagName === "DIALOG") {
            const rect = dialogElement.value?.getBoundingClientRect();
            const insideX = rect && event.clientX >= rect.left && event.clientX <= rect.right;
            const insideY = rect && event.clientY >= rect.top && event.clientY <= rect.bottom;
            if (!(insideX && insideY)) {
                closePalette();
            }
        }
    }

    /**
     * The browser's own escape handling closes a modal dialog outright. Escape in
     * the palette is stepwise, so the close request is cancelled and routed through
     * the same handler the input uses — the input's own escape never reaches here,
     * it prevents the keydown default before a close request is even made.
     */
    function onDialogCancel(event: Event) {
        event.preventDefault();
        if (handleEscape() === "close") {
            closePalette();
        }
    }

    /**
     * The dialog was closed by the platform, so the palette follows — unless the
     * event belongs to a close a reopen has already superseded. The browser fires
     * `close` in a task of its own, and a user gesture is allowed to overtake it, so
     * a ⌘K landing at the end of a fade-out is answered (the dialog is showing
     * again) before this event is delivered. Honoring it then would swallow the
     * press and leave the palette closed.
     */
    function onDialogClose() {
        if (dialogElement.value?.open) {
            return;
        }
        if (isPaletteOpen.value) {
            closePalette();
        }
    }

    function prefersReducedMotion() {
        return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    /** Two frames: the first paints the closed state, the second starts the transition */
    function afterNextFrame(callback: () => void) {
        if (typeof requestAnimationFrame !== "function") {
            callback();
            return;
        }
        requestAnimationFrame(() => requestAnimationFrame(callback));
    }

    function clearPendingClose() {
        cancelPendingClose?.();
        cancelPendingClose = null;
    }

    async function openDialog() {
        const epoch = ++transitionEpoch;
        // a close still waiting on its fade-out is cancelled outright, listener and
        // fallback timer included: a toggle landing mid-close reopens instead of
        // being swallowed by the close it interrupted
        clearPendingClose();
        await nextTick();
        const dialog = dialogElement.value;
        if (!dialog || epoch !== transitionEpoch) {
            return;
        }
        // still open while fading out, or genuinely closed and reopened from scratch
        if (!dialog.open) {
            try {
                dialog.showModal();
            } catch (e) {
                // dialog may already be open, or the test environment lacks support
            }
        }
        inputElement.value?.focus();
        // a preserved query starts out selected: typing replaces it outright, while
        // an arrow key drops the selection and carries on from where it left off
        inputElement.value?.select();
        if (prefersReducedMotion()) {
            paletteVisible.value = true;
            return;
        }
        afterNextFrame(() => {
            if (epoch === transitionEpoch) {
                paletteVisible.value = true;
            }
        });
    }

    function closeDialog() {
        const epoch = ++transitionEpoch;
        clearPendingClose();
        paletteVisible.value = false;
        const dialog = dialogElement.value;
        if (!dialog?.open) {
            return;
        }
        let timeout: ReturnType<typeof setTimeout> | null = null;
        /** Disarms this close, whether it ran or was cancelled by a reopen */
        function disarm() {
            dialog?.removeEventListener("transitionend", onTransitionEnd);
            if (timeout !== null) {
                clearTimeout(timeout);
                timeout = null;
            }
            cancelPendingClose = null;
        }
        function finishClose() {
            disarm();
            if (epoch !== transitionEpoch) {
                // reopened mid-transition, the newer open owns the dialog now
                return;
            }
            dialog?.close();
        }
        function onTransitionEnd(event: TransitionEvent) {
            if (event.target === dialog) {
                finishClose();
            }
        }
        if (prefersReducedMotion()) {
            finishClose();
            return;
        }
        dialog.addEventListener("transitionend", onTransitionEnd);
        timeout = setTimeout(finishClose, CLOSE_TRANSITION_FALLBACK);
        cancelPendingClose = disarm;
    }

    onBeforeUnmount(() => {
        transitionEpoch++;
        clearPendingClose();
    });

    return {
        closeDialog,
        onClickDialog,
        onDialogCancel,
        onDialogClose,
        onDialogMousedown,
        openDialog,
        paletteVisible,
    };
}
