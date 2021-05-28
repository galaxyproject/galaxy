export default class User {
    constructor(props = {}) {
        Object.assign(this, props);
    }

    get isAnonymous() {
        return !this.email;
    }

    get isAdmin() {
        return this?.is_admin || false;
    }

    isSameUser(otherUser) {
        if (this.id) {
            return this.id == otherUser.id;
        }
        return true;
    }
}
