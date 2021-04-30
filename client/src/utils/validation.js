// type utils

// all args not null and not undefined
export const areDefined = (...vals) => vals.every(isDefined);

// not null and not undefined
export const isDefined = (val) => val !== undefined && val !== null;

// defined, number and finite
export const isValidNumber = (val) => isDefined(val) && !isNaN(val) && isFinite(val);
