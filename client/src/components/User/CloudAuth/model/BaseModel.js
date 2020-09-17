const lastState = new WeakMap();
const validators = new WeakMap();
const transients = new WeakMap();
const counter = new WeakMap();

// Helps with Vue for-loop keys
let instanceCounter = 0;

export class BaseModel {
    constructor() {
        counter.set(this, instanceCounter++);
    }

    /* object ID */

    get counter() {
        return counter.get(this);
    }

    /* Dirty state tracking */

    get dirty() {
        return lastState.get(this) != this.state;
    }

    get clean() {
        return !this.dirty;
    }

    get state() {
        // build state JSON ignoring transient fields
        const tFields = this.transientFields;
        return JSON.stringify(this, function (key) {
            if (!tFields.has(key)) {
                return this[key];
            }
            return undefined;
        });
    }

    get lastState() {
        return lastState.get(this);
    }

    get transientFields() {
        const key = this.constructor;
        if (!transients.has(key)) {
            transients.set(key, new Set());
        }
        return transients.get(key);
    }

    updateState() {
        lastState.set(this, this.state);
    }

    // Setting a property name as transient for a class means its
    // state will be caclulated without regard to that propety
    static setTransient(...fieldNames) {
        const klass = this; // this will be a class
        if (!transients.has(klass)) {
            transients.set(klass, new Set());
        }

        const fields = transients.get(klass);
        fieldNames.forEach((fieldName) => fields.add(fieldName));
        transients.set(klass, fields);
    }

    /* Validation */

    get valid() {
        return Object.keys(this.validationErrors).length == 0;
    }

    get validationErrors() {
        return this.constructor.validate(this);
    }

    errorMessage(field) {
        if (field in this.validationErrors) {
            return this.validationErrors[field];
        }
        return "errmessage";
    }

    fieldValid(fieldName) {
        return !(fieldName in this.validationErrors);
    }

    static validate(model) {
        if (validators.has(this)) {
            const validator = validators.get(this);
            return validator(model);
        }
        throw new Error("Missing validator");
    }

    static setValidator(validationFunction) {
        validators.set(this, validationFunction);
    }
}
