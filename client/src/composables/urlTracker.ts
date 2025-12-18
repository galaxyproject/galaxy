import { computed, type DeepReadonly, readonly, type Ref, ref } from "vue";

interface UrlTrackerOptions<T> {
    root?: T;
}

interface GetUrlResult<T> {
    url: T;
    popped?: T;
}

interface UseUrlTrackerReturn<T> {
    atRoot: Readonly<Ref<boolean>>;
    navigationHistory: DeepReadonly<Ref<T[]>>;
    getUrl(url?: T, returnWithPrevious?: false): T;
    getUrl(url: T | undefined, returnWithPrevious: true): GetUrlResult<T>;
    reset(newRoot?: T): void;
}

/**
 * Composable for tracking URL navigation history with stack-based drill-down behavior.
 *
 * Manages a navigation stack for hierarchical data exploration, allowing users to
 * drill into nested structures and navigate back through their history.
 *
 * @template T - The type of navigation items (e.g., string URLs or navigation objects)
 * @param options - Configuration options
 * @param options.root - The root/initial URL to return when stack is empty
 *
 * @example
 * // String-based navigation
 * const tracker = useUrlTracker<string>({ root: '/api/data' });
 * tracker.getUrl('/api/data/folder1'); // Navigate forward
 * tracker.getUrl(); // Navigate back
 *
 * @example
 * // Object-based navigation with metadata
 * const tracker = useUrlTracker<NavigationItem>({ root: { id: 'root', url: '/' } });
 * tracker.getUrl({ id: '1', url: '/folder', page: 1 }); // Navigate with state
 * const result = tracker.getUrl(undefined, true); // Go back with popped value
 */
export function useUrlTracker<T = unknown>(options: UrlTrackerOptions<T> = {}): UseUrlTrackerReturn<T> {
    const root = ref(options.root) as Ref<T>;
    const navigation = ref<T[]>([]) as Ref<T[]>;

    const atRoot = computed(() => navigation.value.length === 0);

    function getUrl(url?: T, returnWithPrevious?: false): T;
    function getUrl(url: T | undefined, returnWithPrevious: true): GetUrlResult<T>;
    function getUrl(url?: T, returnWithPrevious = false): T | GetUrlResult<T> {
        let previous: T | undefined = undefined;

        if (url !== undefined) {
            // Navigate forward - push to stack
            navigation.value.push(url);
        } else {
            // Navigate backward - pop from stack
            previous = navigation.value.pop();
            const navigationLength = navigation.value.length;

            if (navigationLength > 0) {
                // Return the new top of stack
                url = navigation.value[navigationLength - 1];
            } else {
                // Stack is empty, return root
                url = root.value;
            }
        }

        if (returnWithPrevious) {
            return { url: url as T, popped: previous };
        } else {
            return url as T;
        }
    }

    /**
     * Resets the navigation stack and optionally updates the root.
     *
     * @param newRoot - Optional new root value to set
     */
    function reset(newRoot?: T): void {
        if (newRoot !== undefined) {
            root.value = newRoot;
        }
        navigation.value = [];
    }

    return {
        atRoot: readonly(atRoot),
        navigationHistory: readonly(navigation),
        getUrl,
        reset,
    };
}
