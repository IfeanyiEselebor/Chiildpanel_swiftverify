const removeIntercomChat = async () => {
    if (window.Intercom) {
        window.Intercom('update', { "hide_default_launcher": true });
    }
}
const showIntercomChat = async () => {
    if (window.Intercom) {
        window.Intercom('update', { "hide_default_launcher": false });
    }
}
const waitForElement = async (selector) => {
    return new Promise(resolve => {
        if (document.querySelector(selector)) {
            return resolve(document.querySelector(selector));
        }
        const observer = new MutationObserver(mutations => {
            if (document.querySelector(selector)) {
                resolve(document.querySelector(selector));
                observer.disconnect();
            }
        });
        observer.observe(document.body,
            {
                childList: true,
                subtree: true
            });
    });
}
const scrollToElementId = async (elementId) => {
    var target = await waitForElement("[id='" + elementId + "']");
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
const scrollToRelativeElementId = async (elementId) => {
    var target = await waitForElement("[id='" + elementId + "']");
    target.scrollTop = 0;
}
window.showIntercomChat = showIntercomChat;
window.removeIntercomChat = removeIntercomChat;
window.waitForElement = waitForElement;
window.scrollToElementId = scrollToElementId;
window.scrollToRelativeElementId = scrollToRelativeElementId;
