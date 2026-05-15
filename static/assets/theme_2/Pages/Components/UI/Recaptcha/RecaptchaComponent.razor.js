let _selector;
let _siteKey;
let _dotNetObj;
let _loadingFinished;
//global so that recaptcha callback and be triggered.
window.onloadRecaptchaCallback = async function onloadRecaptchaCallback() {
    console.log('gc start');
    var id = grecaptcha.render(_selector, {
        'sitekey': _siteKey,
        'callback': (response) => {
            _dotNetObj.invokeMethodAsync('OnSuccessCallback', response);
        },
        'expired-callback': () => {
            _dotNetObj.invokeMethodAsync('OnExpiredCallback');
        }
    });

    await new Promise(r => setTimeout(r, 200));
    _dotNetObj.invokeMethodAsync('FinishedRendering');
    console.log('gc end: ' + id);
    _loadingFinished(id);
    console.log('gc end2: ' + id);

}
export async function render(dotNetObj, selector, siteKey) {

    console.log('gc render start');
    _dotNetObj = dotNetObj;
    _selector = selector;
    _siteKey = siteKey;
    await loadScript('https://www.google.com/recaptcha/api.js?onload=onloadRecaptchaCallback&render=explicit');

    console.log('gc render end');
    return new Promise(function (resolve, reject) {
        _loadingFinished = resolve;
    });
}

export function getResponse(widgetId) {
    return grecaptcha.getResponse(widgetId);
}

export async function resetRecaptcha(widgetId) {
    console.log('reset: ' + widgetId);
    await _loadingFinished;
    return grecaptcha.reset(widgetId);
}
export async function loadScript(url) {
    return new Promise((resolve, reject) => {
        console.log('loading g script');

        var script = document.createElement("script");
        script.src = url;
        script.onload = () => { console.log('g script loaded'); resolve(); }
        document.head.appendChild(script);
    });
}