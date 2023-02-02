/** length of const array or tuple */
export type Length<T extends any[]> = T["length"];

/** build a tuple with length L, and type T */
export type Tuple<L extends number, T = any, R extends T[] = []> = R extends { length: L } ? R : Tuple<L, T, [...R, T]>;

/** adds two constant positive whole number types */
export type Add<A extends number, B extends number> = Length<[...Tuple<A>, ...Tuple<B>]>;

/** subtracts one constant positive whole number type from another */
export type Subtract<A extends number, B extends number> = Tuple<A> extends [...infer U, ...Tuple<B>]
    ? Length<U>
    : never;

/** type of the last element of a readonly array or tuple */
export type Last<A extends readonly [...any]> = A[Subtract<Length<A>, 1>];

/** type of the first element of a readonly array or tuple */
export type First<A extends readonly [...any]> = A[Length<A>];
