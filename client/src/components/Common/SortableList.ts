import draggable from "vuedraggable";

/**
 * vuedraggable 4 is written for Vue 3 and calls its `item` slot with
 * `{ element, index }`. Under @vue/compat MODE 2 a component with a render
 * function gets its `$slots` wrapped in the Vue 2 style proxy, which calls every
 * slot with no arguments, so the slot props arrive as `undefined`. Opting this
 * one component into MODE 3 keeps it out of that wrapping.
 */
const SortableList = { ...draggable, compatConfig: { MODE: 3 } } as typeof draggable;

export default SortableList;
