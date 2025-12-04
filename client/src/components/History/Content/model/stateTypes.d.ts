import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";

import type { STATES } from "./states";

export type State = {
    status: string;
    text?: string;
    icon?: IconDefinition;
    spin?: boolean;
    nonDb?: boolean;
};

export type States = {
    [_key in keyof typeof STATES]: State;
};

export interface HelpText {
    [key: string]: string;
}
