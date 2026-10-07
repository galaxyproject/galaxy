import { useEventListener } from "@vueuse/core";
import { computed, ref } from "vue";

import { useEventStore } from "@/stores/eventStore";

function isNewTabModifier(key: string) {
    return key === "Meta" || key === "Control";
}

/** Whether the key stands for a character, the way a shifted letter does */
function isTextKey(key: string) {
    return key.length === 1;
}

/** Window key tracking: held modifiers for the hint preview, ctrl/cmd+K for `onToggle` */
export function usePaletteModifiers(onToggle: () => void) {
    const eventStore = useEventStore();

    /** Whether ctrl/cmd is currently down, so the palette can preview "new tab" */
    const modifierHeld = ref(false);
    /** Whether shift is currently down, so the palette can preview the secondary run */
    const shiftHeld = ref(false);

    const modifierLabel = computed(() => (eventStore.isMac ? "⌘" : "Ctrl+"));

    function releaseModifiers() {
        modifierHeld.value = false;
        shiftHeld.value = false;
    }

    useEventListener(window, "keydown", (event: KeyboardEvent) => {
        if (isNewTabModifier(event.key)) {
            modifierHeld.value = true;
        }
        if (event.key === "Shift") {
            // a held shift auto-repeats, and only its first press may turn the
            // preview back on: the character below has to keep it off
            if (!event.repeat) {
                shiftHeld.value = true;
            }
        } else if (isTextKey(event.key)) {
            // unlike ctrl/cmd, shift is how a capital is typed: the moment it
            // produces a character it is text entry, not a `⇧↵` the user is weighing
            shiftHeld.value = false;
        }
        const platformModifier = eventStore.isMac ? event.metaKey : event.ctrlKey;
        if (event.key.toLowerCase() === "k" && platformModifier && !event.shiftKey && !event.altKey && !event.repeat) {
            event.preventDefault();
            onToggle();
        }
    });

    useEventListener(window, "keyup", (event: KeyboardEvent) => {
        if (isNewTabModifier(event.key)) {
            modifierHeld.value = false;
        }
        if (event.key === "Shift") {
            shiftHeld.value = false;
        }
    });

    // opening a new tab moves focus away, so the matching keyup never arrives here
    useEventListener(window, "blur", releaseModifiers);

    return { modifierHeld, modifierLabel, releaseModifiers, shiftHeld };
}
