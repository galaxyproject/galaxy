// Own module, so Vue skips the runtime prop check: [String, null, Function] rejects elements and functions.
/** Element id, element, or getter such as `() => $refs.x` (a component resolves to its root element) */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PopoverTarget = string | Element | (() => any);
