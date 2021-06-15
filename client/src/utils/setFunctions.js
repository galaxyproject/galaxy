// Replace with a good standard lib maybe?

export function setEquals(A, B) {
    const X = intersection(A, B);
    return A.size == X.size && B.size == X.size;
}

export function intersection(A, B) {
    return new Set([...A].filter((x) => B.has(x)));
}
