let counter = 0;
export class ScrollPos {
    constructor(props = {}) {
        const { cursor = 0.0, key = null } = props;
        this.cursor = cursor;
        this.key = key;
        counter++;
        this.id = counter;
    }
}

ScrollPos.create = function (props) {
    const o = new ScrollPos(props);
    return Object.freeze(o);
};

ScrollPos.equals = function (a, b) {
    return a.cursor == b.cursor && a.key == b.key;
};
