export function rethrowSimple(e) {
    let message = "Request failed.";
    if (e.response) {
        message = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
    } else if (typeof e == "string") {
        message = e;
    }
    throw message;
}
