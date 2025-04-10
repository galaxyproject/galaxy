import type { Ref } from "vue";

import type Filtering from "@/utils/filtering";

export interface SelectedItemsProps<T> {
    /** A unique key to watch and reset selection when it changes. */
    scopeKey: Ref<string>;
    /** A method that returns a unique key for each item. */
    getItemKey: (item: T) => string;
    /** The current filter text. */
    filterText: Ref<string>;
    /** The count of items in the current query. */
    totalItemsInQuery: Ref<number>;
    /** A list of all items. */
    allItems: Ref<T[]>;
    /** The filtering class used to check query selection. */
    filterClass: Filtering<any>;
    /** If the items are selectable. */
    selectable: Ref<boolean>;
    /** A method called when the "Query Selection Mode" is broken. */
    querySelectionBreak?: () => void;
    /** A method called when an item is deleted. */
    onDelete: (item: T, recursive: boolean) => void;
    /** The class name for the element that is used for keydown selection/navigation. */
    expectedKeyDownClass?: string;
    /** A list of class names that are not allowed to be used for keydown selection/navigation. */
    disallowedKeyDownClasses?: string[];
    /** The element attribute used for range selection.
     * @default "id"
     * @example Could instead be `data-id` in
     *          ```html
     *          <div data-id="1">
     *          ```
     */
    attributeForRangeSelection?: string;
}

export type ComponentInstanceRef<T extends ComponentInstanceExtends> = Record<string, Ref<InstanceType<T> | null>>;
export type ComponentInstanceExtends = abstract new (...args: any) => any;
