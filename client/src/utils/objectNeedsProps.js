// Object must have indicated required property values values
export const objectNeedsProps = (requiredProps = []) => (val = {}) => {
    return requiredProps.reduce((result, fieldName) => result && fieldName in val, true);
};
