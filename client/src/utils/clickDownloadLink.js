/**
 * Creates a temporary link in the body of the document, then clicks on it to initiate a standard
 * download with filename set by the content-disposition header of the response.
 *
 * @param   {string}  href  Link href
 */
export function clickDownloadLink(href, opts = {}) {
    const { filename = "", linkLifetime = 1000 } = opts;

    // make a link
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = href;

    // technically you can set the save file name, but content-disposition from the response
    // headers has precedence over this value, so it may not do anything
    a.setAttribute("download", filename);

    // add to doc and click
    document.body.appendChild(a);
    a.click();

    // remove link after clicking
    setTimeout(() => document.body.removeChild(a), linkLifetime);
}
