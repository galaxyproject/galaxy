import { computed } from "vue";

export interface HasTitleProps {
    title?: string;
    disabledTitle?: string;
    disabled?: boolean;
}

/**
 * Picks the correct title based on the disabled state of a component
 */
export function useCurrentTitle(props: HasTitleProps) {
    const currentTitle = computed(() => {
        if (props.disabled) {
            return props.disabledTitle ?? props.title;
        } else {
            return props.title;
        }
    });

    return currentTitle;
}
