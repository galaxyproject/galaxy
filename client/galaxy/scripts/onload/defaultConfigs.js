import { getRootFromIndexLink } from "./getRootFromIndexLink";

export const defaultConfigs = {
    options: {
        root: getRootFromIndexLink()
    },
    bootstrapped: {},
    form_input_auto_focus: false,
    sentry: {}
};
