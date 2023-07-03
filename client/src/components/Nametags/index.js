import { mountVueComponent } from "utils/mountVueComponent";

import Nametags from "./Nametags";

export { default as Nametag } from "./Nametag.vue";
export { default as Nametags } from "./Nametags.vue";
export const mountNametags = mountVueComponent(Nametags);
