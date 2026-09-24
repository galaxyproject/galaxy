/**
 * What a GPopover anchors to: an element id, an element, or a getter such as `() => $refs.x`, where a
 * component instance resolves to its root element. Kept in its own module so Vue compiles no runtime
 * check for the prop, which would reject every element and function with "null is not a constructor".
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type PopoverTarget = string | Element | (() => any);
