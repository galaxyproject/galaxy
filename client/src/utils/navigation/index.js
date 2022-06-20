import NAVIGATION_DATA from "./navigation.yml";

function interpolate(template, properties) {
    let parsed = template;
    parsed = parsed.replace("$$", "$"); // Handle escaping $ in Python style...
    Object.keys(properties).forEach((key) => {
        const value = properties[key];
        parsed = parsed.replace("${" + key + "}", value);
    });
    return parsed;
}

class SelectorTemplate extends Function {
    constructor(selector, selectorType, props = {}, children = {}) {
        super();
        if (selectorType == "data-description") {
            selectorType = "css";
            selector = `[data-description="${selector}"]`;
        }
        this._selector = selector;
        this.selectorType = selectorType;
        this._props = props || {};
        return new Proxy(this, {
            apply: (target, thisArg, args) => target._call(args),
        });
    }

    _call(args) {
        const inputProps = args[0];
        const allProps = { ...this._props, ...inputProps };
        return new SelectorTemplate(this._selector, this.selectorType, allProps, this.children);
    }

    get description() {
        const selector = this.selector;
        let desc;
        if (this.selectorType == "css") {
            desc = `CSS selector [${selector}]`;
        } else if (this.selectorType == "xpath") {
            desc = `XPATH selector [${selector}]`;
        } else if (this.selectorType == "id") {
            desc = `DOM element with id [${selector}]`;
        }
        return desc;
    }

    get selector() {
        return interpolate(this._selector, this._props);
    }
}

function selectorTemplateFromObject(object, children = {}) {
    if (typeof object === "string" || object instanceof String) {
        const selector = object;
        return new SelectorTemplate(selector, "css", {}, children);
    } else {
        const selectorType = object.type || "css";
        const selector = object.selector;
        return new SelectorTemplate(selector, selectorType, {}, children);
    }
}

function componentFromObject(name, object) {
    const selectors = {};
    const subComponents = {};

    Object.keys(object).forEach((key) => {
        const value = object[key];
        if (key == "selectors") {
            let baseSelector = null;
            const hasBaseSelector = value["_"] !== undefined;
            if (hasBaseSelector) {
                baseSelector = value["_"];
                delete value["_"];
            }
            Object.keys(value).forEach((selectorKey) => {
                const selectorValue = value[selectorKey];
                if (selectorValue == undefined) {
                    throw `Problem with selectors value ${selectorValue}`;
                }
                selectors[selectorKey] = selectorTemplateFromObject(selectorValue);
            });
            if (baseSelector) {
                selectors["_"] = selectorTemplateFromObject(baseSelector, selectors);
            }
        } else if (key == "labels") {
            // implement as needed
        } else if (key == "text") {
            // implement as needed
        } else {
            const component = componentFromObject(key, value);
            subComponents[key] = component;
        }
    });
    return new Component(name, subComponents, selectors);
}

class Component {
    constructor(name, subComponents, selectors) {
        self._name = name;
        self._subComponents = subComponents;
        self._selectors = selectors;
        const component = this;

        Object.keys(subComponents).forEach((key) => {
            const value = subComponents[key];
            component[key] = value;
        });
        Object.keys(selectors).forEach((key) => {
            const value = selectors[key];
            component[key] = value;
        });
    }

    get selector() {
        if (hasOwnProperty("_")) {
            return this["_"];
        } else {
            throw `No _ selector for [${this}]`;
        }
    }
}

export const ROOT_COMPONENT = componentFromObject("root", NAVIGATION_DATA);
