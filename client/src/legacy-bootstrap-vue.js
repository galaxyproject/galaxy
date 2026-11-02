// The three bootstrap-vue components that are plain option objects instead of
// going through Vue.extend (they define their props lazily), so the extend
// hook in legacy-libraries.js never sees them.
import { BCol, BFormGroup, BRow } from "bootstrap-vue";

import { legacyComponent } from "./legacy-libraries";

[BCol, BFormGroup, BRow].forEach((component) => legacyComponent(component));
