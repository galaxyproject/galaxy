import { inject, type InjectionKey, type Ref, ref } from "vue";

export const embedKey: InjectionKey<Readonly<Ref<boolean>>> = Symbol("embed");

export function useEmbed(): Readonly<Ref<boolean>> {
    return inject(embedKey, ref(false));
}
