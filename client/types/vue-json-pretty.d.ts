// Wont be needed after migration to Vue 3
// https://github.com/leezng/vue-json-pretty/issues/57#issuecomment-750700424
declare module "vue-json-pretty" {
    import { Component } from "vue/types/options";
    const VueJsonPretty: Component;
    export default VueJsonPretty;
}
