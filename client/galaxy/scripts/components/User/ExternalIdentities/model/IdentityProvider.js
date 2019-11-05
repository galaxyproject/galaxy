import { safeAssign } from "utils/safeAssign";

export class IdentityProvider {
    constructor(props = {}) {
        this.id = "";
        this.provider = "";
        this.email = "";
        safeAssign(this, props);
    }

    // Aliases

    get authn_id() {
        return this.id;
    }

    get text() {
        return this.provider;
    }

    get email() {
        return this.email;
    }

    get value() {
        return this.id;
    }

    // Statics

    static create(props = {}) {
        return new IdentityProvider(props);
    }
}
