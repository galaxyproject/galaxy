import { type IconDefinition } from "@fortawesome/free-solid-svg-icons";

export type CardBadgeType = "pill" | "badge";

export interface CardBadge {
    id: string;
    label: string;
    title: string;
    variant?: string;
    icon?: IconDefinition;
    to?: string;
    type?: CardBadgeType;
    visible?: boolean;
    class?: string;
    handler?: () => void;
}

export interface CardAttributes {
    id: string;
    label: string;
    title: string;
    variant?: string;
    icon?: IconDefinition;
    size?: string;
    visible?: boolean;
    disabled?: boolean;
    to?: string;
    href?: string;
    handler?: () => void;
}

export type Title =
    | string
    | {
          label: string;
          title: string;
          handler: () => void;
      };
