/** This Util is used for alerting users who use assistive technologies such as screen readers
 *  @param {String} message
 */
function ariaAlert(message) {
    const alert = document.createElement("p");
    alert.textContent = message;
    alert.setAttribute("role", "alert");
    document.body.appendChild(alert);
    setTimeout(function () {
        document.body.removeChild(alert);
    }, 2000);
}

//==============================================================================
export default ariaAlert;
