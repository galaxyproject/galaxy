import { NON_TERMINAL_STATES } from "components/WorkflowInvocationState/util";
import { snakeCase } from "lodash";

export function stateIsTerminal(result) {
    return !NON_TERMINAL_STATES.includes(result.state);
}

export const HasAttributesMixin = {
    computed: {
        attributes() {
            return this.toCamelCase(this.$attrs);
        },
    },
    methods: {
        toCamelCase(attributes) {
            const result = {};
            for (const key in attributes) {
                const newKey = key.replace(/-./g, (x) => x[1].toUpperCase());
                result[newKey] = attributes[key];
            }
            return result;
        },
    },
};

// Adapt bootstrap parameters to Galaxy API. Galaxy consumes snake case parameters
// and generally uses limit instead of perPage/per_page as a name for this concept.
export function cleanPaginationParameters(requestParams) {
    const cleanParams = {};
    Object.entries(requestParams).map(([key, val]) => {
        if (key === "perPage") {
            key = "limit";
        }
        if (val) {
            cleanParams[snakeCase(key)] = val;
        }
    });
    if (cleanParams.current_page && cleanParams.limit) {
        cleanParams.offset = (cleanParams.current_page - 1) * cleanParams.limit;
        delete cleanParams.current_page;
    }
    return cleanParams;
}
