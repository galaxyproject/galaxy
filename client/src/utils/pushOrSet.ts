export function pushOrSet(object: { [index: string | number]: any[] }, key: string | number, value: any) {
    if (key in object) {
        object[key].push(value);
    } else {
        object[key] = [value];
    }
}
