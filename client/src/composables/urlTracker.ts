import { computed, type DeepReadonly, readonly, type Ref, ref } from "vue";

/**
 * Configuration options for URL tracker.
 */
interface UrlTrackerOptions<T> {
    /** Initial value returned when navigation stack is empty. */
    root?: T;
}

/**
 * Result returned by backwardWithContext() containing both the new current location
 * and the item that was popped from the stack.
 */
interface BackwardWithContextResult<T> {
    /** The current location after navigating backward. */
    current: T;
    /** The item that was removed from the stack, or undefined if already at root. */
    popped: T | undefined;
}

/**
 * Return value of useUrlTracker composable.
 */
interface UseUrlTrackerReturn<T> {
    /** Current location in the navigation stack. Returns root when stack is empty. */
    current: Readonly<Ref<DeepReadonly<T>>>;
    /** Read-only array of all navigation items in the stack. */
    navigationHistory: DeepReadonly<Ref<T[]>>;
    /** Whether currently at root level (stack is empty). */
    isAtRoot: Readonly<Ref<boolean>>;
    /** Navigate forward by pushing an item onto the stack. */
    forward(item: T): void;
    /** Navigate backward by popping from the stack. Returns current location after going back. */
    backward(): T;
    /** Navigate backward and return both new current location and popped item. */
    backwardWithContext(): BackwardWithContextResult<T>;
    /** Alias for forward(). */
    push(item: T): void;
    /** Alias for backward(). */
    pop(): T;
    /** Clear navigation stack and optionally set new root. */
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
 * tracker.forward('/api/data/folder1'); // Navigate forward
 * console.log(tracker.current.value); // '/api/data/folder1'
 * tracker.backward(); // Navigate back
 * console.log(tracker.current.value); // '/api/data'
 *
 * @example
 * // Object-based navigation with metadata
 * const tracker = useUrlTracker<NavigationItem>({ root: { id: 'root', url: '/' } });
 * tracker.forward({ id: '1', url: '/folder', page: 1 }); // Navigate with state
 * const { current, popped } = tracker.backwardWithContext(); // Go back with popped value
 * if (popped) {
 *   console.log('Restored page:', popped.page);
 * }
 *
 * @example
 * // Using push/pop aliases
 * const tracker = useUrlTracker<string>({ root: '/root' });
 * tracker.push('/folder1'); // Same as forward()
 * tracker.pop(); // Same as backward()
 */
export function useUrlTracker<T = unknown>(options: UrlTrackerOptions<T> = {}): UseUrlTrackerReturn<T> {
    const root = ref(options.root) as Ref<T | undefined>;
    const navigation = ref<T[]>([]) as Ref<T[]>;

    /**
     * Returns the current location in the navigation stack.
     * When the stack is empty, returns the root value.
     */
    const current = computed(() => {
        const length = navigation.value.length;
        if (length > 0) {
            return navigation.value[length - 1];
        }
        return root.value;
    });

    /**
     * Checks if the navigation is at the root level (stack is empty).
     *
     * @returns true if at root, false otherwise
     */
    const isAtRoot = computed(() => navigation.value.length === 0);

    /**
     * Navigates forward by pushing an item onto the navigation stack.
     *
     * @param item - The navigation item to push onto the stack
     */
    function forward(item: T): void {
        navigation.value.push(item);
    }

    /**
     * Navigates backward by popping the last item from the stack.
     * If already at root, returns the root value (idempotent).
     *
     * @returns The current location after going back
     */
    function backward(): T {
        if (navigation.value.length > 0) {
            navigation.value.pop();
        }
        return current.value as T;
    }

    /**
     * Navigates backward and returns both the new current location and the popped item.
     * Useful when you need to restore state from the popped item (e.g., pagination).
     *
     * @returns Object containing the current location and the popped item (undefined if at root)
     */
    function backwardWithContext(): BackwardWithContextResult<T> {
        const popped = navigation.value.length > 0 ? navigation.value.pop() : undefined;
        return {
            current: current.value as T,
            popped,
        };
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
        current: readonly(current) as Readonly<Ref<DeepReadonly<T>>>,
        navigationHistory: readonly(navigation),
        isAtRoot: readonly(isAtRoot),
        forward,
        backward,
        backwardWithContext,
        push: forward, // Alias for stack-based terminology
        pop: backward, // Alias for stack-based terminology
        reset,
    };
}
