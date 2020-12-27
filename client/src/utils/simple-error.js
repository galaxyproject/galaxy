export function errorMessageAsString(e) {
    let message = "Request failed.";
    if (e && e.response && e.response.data && e.response.data.err_msg) {
        message = e.response.data.err_msg;
    } else if (e && e.response) {
        message = `${e.response.statusText} (${e.response.status})`;
    } else if (typeof e == "string") {
        message = e;
    }
    return message;
}

export function rethrowSimple(e) {
    console.debug(e);
    throw errorMessageAsString(e);
}
