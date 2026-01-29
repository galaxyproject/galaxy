import { RouterLink } from "vue-router";

export interface ClickableProps {
    to?: string;
    href?: string;
}

/**
 * returns the correct type of clickable root element based on a components props.
 */
export function useClickableElement(props: ClickableProps) {
    if (props.to) {
        return RouterLink;
    } else if (props.href) {
        return "a" as const;
    } else {
        return "button" as const;
    }
}
