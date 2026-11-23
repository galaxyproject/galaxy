// The three bootstrap-vue components that are plain option objects instead of
// going through Vue.extend (they define their props lazily), so the extend
// hook in legacy-libraries.js never sees them.
import { BButton, BCol, BFormGroup, BRow } from "bootstrap-vue";

import { LEGACY_COMPAT_CONFIG, legacyComponent } from "./legacy-libraries";

[BCol, BFormGroup, BRow].forEach((component) => legacyComponent(component));

// If bootstrap-vue was evaluated before the extend hook (a chunking or
// prebundling change), its components quietly run under MODE 3. Say so.
if (BButton.options?.compatConfig !== LEGACY_COMPAT_CONFIG) {
    console.error(
        "bootstrap-vue loaded before legacy-libraries.js; its components are not on compat MODE 2. See compat-config.js.",
    );
}
