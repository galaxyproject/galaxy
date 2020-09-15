export function errorMessageAsString(e) {
    let message = "Request failed.";
    if (e.response) {
        message = e.response.data.err_msg || `${e.response.statusText} (${e.response.status})`;
    } else if (typeof e == "string") {
        message = e;
    }
    return message;
}

export function rethrowSimple(e) {
    console.debug(e);
    throw errorMessageAsString(e);
}
