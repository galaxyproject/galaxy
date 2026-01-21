/**
 * Renderless component, used to debounce various types of form inputs
 */

import { Subject } from "rxjs";
import { debounceTime, distinctUntilChanged, filter, finalize } from "rxjs/operators";
import { onBeforeMount, onUnmounted, ref, watch } from "vue";

export default {
    props: {
        value: { required: true },
        delay: { type: Number, required: false, default: 500 },
    },
    emits: ["input"],
    setup(props, { slots, emit }) {
        const previousEmit = ref(null);
        const incomingValue = ref(null);
        const subscription = ref(null);
        const subject = ref(null);

        function sendUpdate(val) {
            if (val !== previousEmit.value) {
                emit("input", val);
                previousEmit.value = val;
            }
        }

        // Watch for immediate changes when delay is 0
        watch(incomingValue, (val) => {
            if (props.delay === 0) {
                sendUpdate(val);
            }
        });

        onBeforeMount(() => {
            if (props.delay !== 0) {
                // Create a subject for incoming values
                subject.value = new Subject();

                const debounced$ = subject.value.pipe(
                    debounceTime(props.delay),
                    distinctUntilChanged(),
                    filter((val) => val !== null && val !== props.value),
                    finalize(() => sendUpdate(incomingValue.value)),
                );

                subscription.value = debounced$.subscribe((val) => sendUpdate(val));
            }
        });

        onUnmounted(() => {
            // Clean up subscription
            if (subscription.value) {
                subscription.value.unsubscribe();
            }
            if (subject.value) {
                subject.value.complete();
            }
        });

        // Watch for changes to incomingValue and push to subject
        watch(incomingValue, (val) => {
            if (props.delay !== 0 && subject.value && val !== null) {
                subject.value.next(val);
            }
        });

        return () => {
            if (!slots.default) {
                return null;
            }
            return slots.default({
                value: props.value,
                input: (e) => {
                    // Vue Bootstrap does not conform to the standard
                    // event object format, so check there first
                    incomingValue.value = e && e.target ? e.target.value : e;
                },
            });
        };
    },
};
