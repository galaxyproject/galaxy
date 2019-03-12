import Badges from "./Badges";
import { mountVueComponent } from "utils/mountVueComponent";

export { default as Badge } from "./Badge.vue";
export { default as Badges } from "./Badges.vue";
export const mountBadges = mountVueComponent(Badges);
