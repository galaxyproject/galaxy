import { type Ref, watch } from "vue";

/**
 * Emits an event whenever a value changes
 * @param ref value to watch
 * @param emit event emitter function
 * @param name event to emit
 */
export function useEmit<Name extends string, T, F extends { (name: Name, arg: T): void }>(
    ref: Ref<T>,
    emit: F,
    name: Name
) {
    watch(
        () => ref.value,
        () => {
            emit(name, ref.value);
        }
    );
}
