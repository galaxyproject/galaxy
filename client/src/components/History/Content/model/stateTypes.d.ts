import { STATES } from "./states";

export type State = {
    status: string;
    text?: string;
    icon?: string;
    spin?: boolean;
};

export type States = {
    [key in keyof typeof STATES]: State;
};

export interface HelpText {
    [key: string]: string;
}
