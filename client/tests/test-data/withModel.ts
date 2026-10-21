import { type Component, defineComponent, h, ref } from "vue";

/**
 * A harness for `component` that plays the parent's part of v-model: every `input` it emits
 * comes back as its `value`. List the harness in the stories meta's `excludeStories`.
 */
export function withModel(component: Component, name: string) {
    return defineComponent({
        name,
        inheritAttrs: false,
        setup(_props, { attrs }) {
            const value = ref(attrs.value);
            return () =>
                h(component, {
                    ...attrs,
                    value: value.value,
                    onInput: (newValue: unknown) => {
                        value.value = newValue;
                    },
                });
        },
    });
}
