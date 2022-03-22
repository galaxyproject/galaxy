import { safeAssign } from "utils/safeAssign";
import { ResourceProviders } from "./ResourceProviders";
import { BaseModel } from "./BaseModel";

export class Credential extends BaseModel {
    constructor(props = {}) {
        super();

        this.id = null;
        this.description = "";
        this.authn_id = null; // identity provider
        this.provider = null; // resource provider

        // transient props, exclude from state
        this.expanded = false;
        this.loading = false;

        // populate props
        const options = Object.assign({}, Credential.defaults, props);
        safeAssign(this, options);

        // init nested config
        this.config = new this.configClass(options.config);

        // initialize state
        this.updateState();
    }

    get title() {
        return this.description.length ? this.description : this.provider;
    }

    get valid() {
        return super.valid && this.config.valid;
    }

    // Alias for provider also changes config object when updated
    // Set this when updating in the UI

    get resourceProvider() {
        return this.provider;
    }

    set resourceProvider(newProvider) {
        this.provider = newProvider;
        this.config = new this.configClass({});
    }

    // Polymorphic config class

    get configClass() {
        return ResourceProviders.get(this.provider).klass;
    }

    // Methods

    match(searchText = "") {
        // TODO: more robust object matching?
        return searchText.length ? this.title.includes(searchText) : true;
    }

    // Statics

    static get defaults() {
        return {
            authn_id: null,
            provider: "aws",
            expanded: false,
        };
    }

    static create(props = {}) {
        return new Credential(props);
    }
}

/**
 * Transient fields do not factor into the state
 * for purposes of dirty tracking
 */
Credential.setTransient("expanded", "loading");

/**
 * A validator function's job is to return an object
 * where the keys are field names and the values are
 * error messages.
 */
Credential.setValidator(function (model) {
    const errors = {};

    if (!model.provider) {
        errors.provider = "Provider must be set";
    }

    if (!model.authn_id) {
        errors.authn_id = "Please pick an identity provider";
    }

    if (!model.config.valid) {
        errors.config = "Invalid config object";
    }

    return errors;
});
