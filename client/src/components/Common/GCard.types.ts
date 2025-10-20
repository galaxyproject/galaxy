import type { SizeProp } from "@fortawesome/fontawesome-svg-core";
import type { IconDefinition } from "@fortawesome/free-solid-svg-icons";

import type { BootstrapVariant } from "@/components/Common";

/** Card badge display styles */
export type CardBadgeType = "pill" | "badge";

/** Bootstrap component sizes */
export type BootstrapSize = "xs" | "sm" | "md" | "lg" | "xl";

/** Title sizes for heading components */
export type TitleSize = "xl" | "lg" | "md" | "sm" | "text";

/** Base properties for all card elements */
interface BaseCardElement {
    /** Unique identifier for the element */
    id: string;
    /** Whether the element is disabled */
    disabled?: boolean;
    /** Display label for the element */
    label: string;
    /** Tooltip text for the element */
    title: string;
    /** Whether the element is visible (defaults to true) */
    visible?: boolean;
}

/** Navigation and interaction properties */
interface NavigationProps {
    /** Whether link opens in new tab/window */
    externalLink?: boolean;
    /** External URL to navigate to */
    href?: string;
    /** Vue Router route to navigate to */
    to?: string;
    /** Click handler function */
    handler?: () => void;
}

/** Visual styling properties */
interface StylingProps {
    /** Additional CSS classes */
    class?: string;
    /** FontAwesome icon to display */
    icon?: IconDefinition;
    /** Whether to spin the icon */
    spin?: boolean;
    /** Bootstrap component size */
    size?: BootstrapSize;
    /** Bootstrap variant for styling */
    variant?: BootstrapVariant;
}

/** Card title - string or interactive object */
export type Title =
    | string
    | {
          /** Display label for the clickable title */
          label: string;
          /** Tooltip text for the title */
          title: string;
          /** Click handler for the title */
          handler: () => void;
      };

/** Icon configuration for card titles */
export interface TitleIcon {
    /** Additional CSS classes for the icon */
    class?: string;
    /** FontAwesome icon to display */
    icon: IconDefinition;
    /** Size of the icon */
    size?: SizeProp;
    /** Tooltip text for the icon */
    title?: string;
}

/** Card badge for displaying status or metadata */
export interface CardBadge
    extends BaseCardElement,
        NavigationProps,
        Pick<StylingProps, "variant" | "icon" | "class" | "spin"> {
    /** Badge display type */
    type?: CardBadgeType;
}

/** Card indicator for visual status information */
export interface CardIndicator extends BaseCardElement, NavigationProps, StylingProps {}

/** Interactive card action like buttons or links */
export interface CardAction extends BaseCardElement, NavigationProps, StylingProps {
    /** Whether to display as inline icon button */
    inline?: boolean;
}
