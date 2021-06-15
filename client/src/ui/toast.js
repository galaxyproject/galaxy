import Toastr from "toastr";

// Simple passthrough for now, but this gives us an extension point to work
// against when converting over to either boostrap-specific or vue-based
// toasts.

export const Toast = Toastr;
