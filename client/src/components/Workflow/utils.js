export function redirectOnImport(appRoot, response, isRunFormRedirect = false) {
    isRunFormRedirect
        ? (window.location = `${appRoot}workflows/run?id=${response.id}`)
        : (window.location = `${appRoot}workflows/list?message=${response.message}&status=success`);
}
