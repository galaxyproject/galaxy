import { type IconDefinition } from "@fortawesome/fontawesome-svg-core";

export type ActivityVariant = "primary" | "danger" | "disabled";

export interface Activity {
    // determine wether an anonymous user can access this activity
    anonymous?: boolean;
    // description of the activity
    description: string;
    // unique identifier
    id: string;
    // icon to be displayed in activity bar
    icon: IconDefinition;
    // indicate if this activity can be modified and/or deleted
    mutable?: boolean;
    // indicate wether this activity can be disabled by the user
    optional?: boolean;
    // specifiy wether this activity utilizes the side panel
    panel?: boolean;
    // title to be displayed in the activity bar
    title: string;
    // route to be executed upon selecting the activity
    to?: string | null;
    // tooltip to be displayed when hovering above the icon
    tooltip: string;
    // indicate wether the activity should be visible by default
    visible?: boolean;
    // if activity should cause a click event
    click?: true;
    variant?: ActivityVariant;
}
