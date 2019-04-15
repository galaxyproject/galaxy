import Nametags from "./Nametags";
import { mountVueComponent } from "utils/mountVueComponent";

export { default as Nametag } from "./Nametag.vue";
export { default as Nametags } from "./Nametags.vue";
export const mountNametags = mountVueComponent(Nametags);
