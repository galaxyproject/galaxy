import { safeAssign } from "utils/safeAssign";

export class IdentityProvider {
    constructor(props = {}) {
        this.id = "";
        this.provider = "";
        safeAssign(this, props);
    }

    // Aliases

    get authn_id() {
        return this.id;
    }

    get text() {
        return this.provider;
    }

    get value() {
        return this.id;
    }

    // Statics

    static create(props = {}) {
        return new IdentityProvider(props);
    }
}
