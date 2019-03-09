// Low level stateless UI component
export { default as StatelessTags } from "./StatelessTags";

// Implements data storage logic and click event handling
// This is usually what you'll want to use.
export { default as Tags } from "./Tags";

// functions for mounting the tag editor in non-Vue environments
export { mountMakoTags, mountModelTags } from "./mounts";
