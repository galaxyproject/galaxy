export default class User {
    constructor(props = {}) {
        Object.assign(this, props);
    }

    get isAnonymous() {
        return !this.email;
    }

    static create(props = {}) {
        return new User(props);
    }
}
