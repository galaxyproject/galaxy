import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

/**
 * Shape FontAwesomeIcon requires of an icon that is not registered with
 * FontAwesome -- consumers generate these from their own SVG sources.
 */
export interface CustomIconDefinition {
    iconName: string;
    prefix: string;
    icon: [number, number, never[], string, string | string[]];
}

export type IconLike = IconDefinition | CustomIconDefinition;
