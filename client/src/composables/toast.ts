import { useToast } from "@galaxyproject/galaxy-ui";

export { type ToastOptions, type ToastVariant, useToast } from "@galaxyproject/galaxy-ui";

/**
 * Direct export to simplify usage in Options Api component.
 * Use 'useToast' for the Composition Api instead.
 */
export const Toast = useToast();
