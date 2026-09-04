import { computed } from "vue";
import { RouterLink } from "vue-router";

export interface ClickableProps {
    to?: string;
    href?: string;
    disabled?: boolean;
}

/**
 * Returns the correct type of clickable root element based on a component's props.
 *
 * A disabled component always renders as a plain `button`. Rendering it as a
 * RouterLink (or anchor) would let clicks fall through to navigation: an empty
 * `to`/`href` is not a reliable no-op in vue-router, and relying on the click
 * guard to beat RouterLink's own navigation handler would depend on listener
 * ordering. A plain `button` root has no navigation behaviour to suppress.
 */
export function useClickableElement(props: ClickableProps) {
    return computed(() => {
        if (props.disabled) {
            return "button" as const;
        } else if (props.to) {
            return RouterLink;
        } else if (props.href) {
            return "a" as const;
        } else {
            return "button" as const;
        }
    });
}
