export class ScrollPos {
    constructor(props = {}) {
        const { cursor = null, key = null } = props;
        this.cursor = key === null && cursor === null ? 0 : cursor;
        this.key = key;
    }
}

ScrollPos.create = function (props) {
    const o = new ScrollPos(props);
    return Object.freeze(o);
};

ScrollPos.equals = function (a, b) {
    return a.cursor === b.cursor && a.key === b.key;
};
