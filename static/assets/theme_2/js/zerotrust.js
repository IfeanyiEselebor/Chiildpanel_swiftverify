import { cryptoHelper } from './cryptoHelpers.js';
import { TOTP } from './totp.js';
const globalWindow = globalThis.window;
//export class zerotrustService {
//    private _cryptoHelper = new cryptoHelper();
//    private _derivedKeyStorageKeyName = 'DERIVED_KEY_KEYNAME';
//    constructor() {
//    }
//    private async getFromSessionStorage(extensionId: string, keyName: string) {
//        const parameters = {
//            keyName: keyName
//        };
//        const data = await chrome.runtime.sendMessage(extensionId, { getFromSessionStorage: parameters });
//        return data;
//    }
//    private async getDerivedKey(extensionId: string): Promise<Uint8Array> {
//        const data = await this.getFromSessionStorage(extensionId, this._derivedKeyStorageKeyName);
//        if (!data?.derivedKeyArr) {
//            throw new Error('Not unlocked;');
//        }
//        const byteArr = this._cryptoHelper.base64ToByteArray(data.derivedKeyArr)
//        return byteArr;
//    }
//    private async setSessionStorage(extensionId: string, keyName: string, data: any) {
//        const dataToStore =
//        {
//            keyName: keyName,
//            data: data,
//        };
//        await chrome.runtime.sendMessage(extensionId, { setSessionStorage: dataToStore });
//    }       
//    async doAutoLogin(extensionId: string, request: AutoLoginJsParameters) {
//        //handle each step of automation, using the browser extension as needed
//        const currentDerivedKey = await this.getDerivedKey(extensionId);
//        const session = await (await fetch(request.securedUri)).json() as BrowserAutomationSessionJSDto;
//        const unsecuredUserEncryptionKey = await this._cryptoHelper.aesGcmDecryptSecuredCipherString(session.securedUserEncryptionKey, currentDerivedKey);
//        const unsecuredClusterEncryptionKey = await this._cryptoHelper.aesGcmDecryptSecuredCipherString(session.securedClusterEncryptionKey, unsecuredUserEncryptionKey);
//        const steps = session.steps;
//        let launchLoginTabId;
//        let frameIdExecutionContext = request.continuationFrameId ?? 0;
//        async function getContinuationFrameId(): Promise<number> {
//            const command = {
//                checkFrame: {
//                    tabId: launchLoginTabId,
//                    frameId: frameIdExecutionContext
//                },
//            };
//            if (await chrome.runtime.sendMessage(extensionId, command)) {
//                return frameIdExecutionContext;
//            }
//            return 0;
//        }
//        for (let index = 0; index < steps.length; ++index) {
//            let instruction = steps[index].instructions;
//            console.log(`handling step ${instruction.name}`);
//            if (instruction.launchLogin) {
//                const launchLogin = instruction.launchLogin;
//                let targetLoginUri = launchLogin.loginUri;
//                if (!targetLoginUri) {
//                    console.log(`invalid uri`);
//                    return;
//                }
//                if (launchLogin.isLoginUriEncrypted) {
//                    const paddedPlainTextArr = await this._cryptoHelper.aesGcmDecryptSecuredCipherString(targetLoginUri, unsecuredClusterEncryptionKey);
//                    const paddedPlainText = this._cryptoHelper.byteArrayToText(paddedPlainTextArr);
//                    const unpaddedPlainText = this._cryptoHelper.unpadPlainText(paddedPlainText, launchLogin.paddable);
//                    targetLoginUri = unpaddedPlainText;
//                }
//                let getTabTask = new Promise(async function (resolve, reject) {
//                    if (request.loginFlow == 'SpecificTab') {
//                        resolve(request.continuationTabId);
//                        return;
//                    }
//                    if (request.loginFlow == 'CurrentTab') {
//                        const command = {
//                            getActiveTabId: {},
//                        };
//                        const activeTabId = await chrome.runtime.sendMessage(extensionId, command);
//                        resolve(activeTabId);
//                        return;
//                    }
//                    if (request.loginFlow == 'NewTab') {
//                        const newTabOptions = {
//                            active: false,
//                        } as chrome.tabs.CreateProperties;
//                        const command = {
//                            openNewTab: {
//                                newTabOptions: newTabOptions
//                            },
//                        };
//                        const newTabId = await chrome.runtime.sendMessage(extensionId, command);
//                        resolve(newTabId);
//                        return;
//                    }
//                });
//                launchLoginTabId = await getTabTask;
//                if (launchLogin.clearSession) {
//                    const url = new URL(targetLoginUri);
//                    const domain = url.hostname;
//                    let removalOptions = {
//                        "since": 0,
//                        "origins": [`https://${domain}`, `http://${domain}`],
//                        // "originTypes" : {"unprotectedWeb": true, "protectedWeb": true, "extension": true}
//                    } as chrome.browsingData.RemovalOptions;
//                    let dataToRemove = {
//                        // "cacheStorage": true,
//                        "cookies": true,
//                        // "fileSystems": true,
//                        // "indexedDB": true,
//                        "localStorage": true,
//                        // "serviceWorkers": true,
//                        // "webSQL": true
//                    } as chrome.browsingData.DataTypeSet;
//                    const command = {
//                        clearBrowsingData:
//                        {
//                            removalOptions: removalOptions,
//                            dataToRemove: dataToRemove,
//                        }
//                    };
//                    console.log('clearing session');
//                    await chrome.runtime.sendMessage(extensionId, command);
//                    console.log('cleared session');
//                }
//                //frame id was null/undefined/lost
//                if (!await getContinuationFrameId()) {
//                    console.log('navigating tab ' + launchLoginTabId);
//                    const command = {
//                        navigateTab: {
//                            tabId: launchLoginTabId,
//                            uri: targetLoginUri,
//                        },
//                    };
//                    await chrome.runtime.sendMessage(extensionId, command);
//                    if (launchLogin.loginIFrameLocator?.uriFragment) {
//                        const getAllFramesCommand =
//                        {
//                            listFrames:
//                            {
//                                tabId: launchLoginTabId,
//                            }
//                        };
//                        const getAllFrameDetailsResult: chrome.webNavigation.GetAllFrameResultDetails[] = await chrome.runtime.sendMessage(extensionId, getAllFramesCommand);
//                        //locate frame by uri fragment
//                        for (let i = 0; i < getAllFrameDetailsResult.length; i++) {
//                            let frameResult = getAllFrameDetailsResult[i];
//                            if (frameResult.url.includes(launchLogin.loginIFrameLocator.uriFragment)) {
//                                // Return the matching frame details via callback
//                                frameIdExecutionContext = frameResult.frameId;
//                                break;
//                            }
//                        }
//                        if (!frameIdExecutionContext) {
//                            console.error(`Failed to locate iframe for '${launchLogin.loginIFrameLocator.uriFragment}'`);
//                            return;
//                        }
//                    }
//                }
//                else {
//                    console.log('skip nav, frame defined ' + launchLoginTabId + '/' + await getContinuationFrameId());
//                }
//                const activateTabCommand =
//                {
//                    activateTab:
//                    {
//                        tabId: launchLoginTabId
//                    }
//                }
//                await chrome.runtime.sendMessage(extensionId, activateTabCommand);
//                await new Promise(r => setTimeout(r, launchLogin.delayOnSuccessMS));
//                continue;
//            }
//            if (instruction.navigateToUri) {
//                const command = {
//                    navigateTab: {
//                        tabId: launchLoginTabId,
//                        uri: instruction.navigateToUri.uri,
//                    },
//                };
//                await chrome.runtime.sendMessage(extensionId, command);
//                continue;
//            }
//            if (instruction.detectAlreadyLoggedIn) {
//                if (instruction.detectAlreadyLoggedIn.locationDoesNotContain) {
//                    const getAllFramesCommand =
//                    {
//                        listFrames:
//                        {
//                            tabId: launchLoginTabId,
//                        }
//                    };
//                    const getAllFrameDetailsResult: chrome.webNavigation.GetAllFrameResultDetails[] = await chrome.runtime.sendMessage(extensionId, getAllFramesCommand);
//                    let urlToCompare : string;
//                    //locate frame by uri fragment
//                    for (let i = 0; i < getAllFrameDetailsResult.length; i++) {
//                        let frameResult = getAllFrameDetailsResult[i];
//                        if (frameResult.frameId == await getContinuationFrameId()) {
//                            urlToCompare = frameResult.url;
//                            break;
//                        }
//                    }
//                    for (var i = 0; i < instruction.detectAlreadyLoggedIn.locationDoesNotContain.length; i++) {
//                        const locationToCompare = instruction.detectAlreadyLoggedIn.locationDoesNotContain[i];
//                        if (!urlToCompare.includes(locationToCompare)) {
//                            console.log(`already logged in (via location). aborting autologin.`);
//                            return;
//                        }
//                    }
//                }
//                if (instruction.detectAlreadyLoggedIn.searchPredicates) {
//                    var elementPresenceIndicatesAlreadyLoggedIn = instruction.detectAlreadyLoggedIn.searchPredicates;
//                    for (let i = 0; i < elementPresenceIndicatesAlreadyLoggedIn.length; i++) {
//                        var detectedAlreadyLoggedInElement = await findFirstElement(elementPresenceIndicatesAlreadyLoggedIn[i], await getContinuationFrameId());
//                        if (detectedAlreadyLoggedInElement != null) {
//                            console.log(`already logged in (via css). aborting autologin.`);
//                            return;
//                        }
//                    }
//                }
//            }
//            if (instruction.wait) {
//                await new Promise(r => setTimeout(r, instruction.wait.delayMS));
//                continue;
//            }
//            if (instruction.click) {
//                const click = instruction.click;
//                console.log(`> handling step ${instruction.name} with ${click.searchPredicates.length} predicates`);
//                for (let i = 0; i < click.searchPredicates.length; i++) {
//                    var detectedTotpRequriedDomObject = await findFirstElement(click.searchPredicates[i], await getContinuationFrameId());
//                    if (detectedTotpRequriedDomObject != null) {
//                        console.log(`click success`);
//                        const command =
//                        {
//                            tabId: launchLoginTabId,
//                            domCssSelector: detectedTotpRequriedDomObject.domCssSelector,
//                            frameId: await getContinuationFrameId()
//                        };
//                        await chrome.runtime.sendMessage(extensionId, { clickElement: command });
//                        await new Promise(r => setTimeout(r, click.delayOnSuccessMS));
//                        break;
//                    }
//                }
//            }
//            if (instruction.inputText) {
//                const inputTextInstruction = instruction.inputText;
//                const paddedPlainTextArr = await this._cryptoHelper.aesGcmDecryptSecuredCipherString(inputTextInstruction.cipherString, unsecuredClusterEncryptionKey);
//                const paddedPlainText = this._cryptoHelper.byteArrayToText(paddedPlainTextArr);
//                const unpaddedPlainText = this._cryptoHelper.unpadPlainText(paddedPlainText, inputTextInstruction.paddable);
//                console.log(`> handling step ${instruction.name} with ${inputTextInstruction.searchPredicates.length} predicates`);
//                for (let i = 0; i < inputTextInstruction.searchPredicates.length; i++) {
//                    var detectedTotpRequriedDomObject = await findFirstElement(inputTextInstruction.searchPredicates[i], await getContinuationFrameId());
//                    if (detectedTotpRequriedDomObject != null) {
//                        console.log(`input text success`);
//                        const command =
//                        {
//                            tabId: launchLoginTabId,
//                            domCssSelector: detectedTotpRequriedDomObject.domCssSelector,
//                            textValue: unpaddedPlainText,
//                            frameId: await getContinuationFrameId()
//                        };
//                        await chrome.runtime.sendMessage(extensionId, { setInputText: command });
//                        await new Promise(r => setTimeout(r, inputTextInstruction.delayOnSuccessMS));
//                        break;
//                    }
//                }
//            }
//            if (instruction.totp) {
//                const totp = instruction.totp;
//                console.log(`> handling step ${instruction.name} with ${totp.checkIfRequiredPredicates.length} check predicates and ${totp.inputCodePredicates.length} input predicates`);
//                let detectedTotpRequired: boolean = false;
//                for (let i = 0; i < totp.checkIfRequiredPredicates.length; i++) {
//                    let searchPredicate = totp.checkIfRequiredPredicates[i];
//                    let detectedTotpRequriedDomObject = await findFirstElement(searchPredicate, await getContinuationFrameId());
//                    if (detectedTotpRequriedDomObject != null) {
//                        detectedTotpRequired = true;
//                        break;
//                    }
//                }
//                if (detectedTotpRequired) {
//                    const paddedPlainTextArr = await this._cryptoHelper.aesGcmDecryptSecuredCipherString(totp.cipherString, unsecuredClusterEncryptionKey);
//                    const paddedPlainText = this._cryptoHelper.byteArrayToText(paddedPlainTextArr);
//                    const unpaddedPlainText = this._cryptoHelper.unpadPlainText(paddedPlainText, totp.paddable);
//                    const totpResult = await TOTP.generate(unpaddedPlainText, null);
//                    for (let i = 0; i < totp.inputCodePredicates.length; i++) {
//                        let domObject = await findFirstElement(totp.inputCodePredicates[i], await getContinuationFrameId());
//                        if (domObject != null) {
//                            const command =
//                            {
//                                tabId: launchLoginTabId,
//                                domCssSelector: domObject.domCssSelector,
//                                textValue: totpResult.otp,
//                                frameId: await getContinuationFrameId()
//                            };
//                            await chrome.runtime.sendMessage(extensionId, { setInputText: command });
//                            await new Promise(r => setTimeout(r, totp.delayOnSuccessMS));
//                            break;
//                        }
//                    }
//                }
//            }
//            if (instruction.phoneOtp) {
//                const phoneOtp = instruction.phoneOtp;
//                await new Promise(r => setTimeout(r, phoneOtp.delayBetweenChecksMS));
//                console.log(`> handling step ${instruction.name} with ${phoneOtp.checkIfRequiredPredicates.length} check predicates and ${phoneOtp.inputCodePredicates.length} input predicates`);
//                let detectPhoneOtpRequired: boolean = false;
//                for (let i = 0; i < phoneOtp.checkIfRequiredPredicates.length; i++) {
//                    let searchPredicate = phoneOtp.checkIfRequiredPredicates[i];
//                    let detectedTotpRequriedDomObject = await findFirstElement(searchPredicate, await getContinuationFrameId());
//                    if (detectedTotpRequriedDomObject != null) {
//                        detectPhoneOtpRequired = true;
//                        break;
//                    }
//                }
//                if (!detectPhoneOtpRequired) {
//                    console.log("phone otp not detected.");
//                    break;
//                }
//                let requestedCode = false;
//                for (let i = 0; i < phoneOtp.requestCodePredicates.length; i++) {
//                    let searchPredicate = phoneOtp.requestCodePredicates[i];
//                    let requestCodeDomObject = await findFirstElement(searchPredicate, await getContinuationFrameId());
//                    if (requestCodeDomObject != null) {
//                        const command =
//                        {
//                            tabId: launchLoginTabId,
//                            domCssSelector: requestCodeDomObject.domCssSelector,
//                            frameId: await getContinuationFrameId()
//                        };
//                        await chrome.runtime.sendMessage(extensionId, { clickElement: command });
//                        requestedCode = true;
//                        break;
//                    }
//                }
//                if (!requestedCode) {
//                    console.log("phone otp not requested");
//                    break;
//                }
//                // poll the uri for the code
//                console.log("waiting for phone otp code");
//                const codeResponse = await (await fetch(phoneOtp.phoneOtpUri)).json();
//                let otpInputed = false;
//                if (codeResponse.codes) {
//                    console.log('received otp code');
//                    for (let i = 0; i < phoneOtp.inputCodePredicates.length; i++) {
//                        let searchPredicate = phoneOtp.inputCodePredicates[i];
//                        let inputCodeDomObject = await findFirstElement(searchPredicate, await getContinuationFrameId());
//                        const command =
//                        {
//                            tabId: launchLoginTabId,
//                            domCssSelector: inputCodeDomObject.domCssSelector,
//                            textValue: codeResponse.codes[0],
//                            frameId: await getContinuationFrameId()
//                        };
//                        await chrome.runtime.sendMessage(extensionId, { setInputText: command });
//                        otpInputed = true;
//                        break;
//                    }
//                }
//                if (otpInputed) {
//                    //click whatver stupid option..
//                    //phoneOtp.rememeberMePredicates
//                    //phoneOtp.submitCodePredicates
//                    for (let i = 0; i < phoneOtp.submitCodePredicates.length; i++) {
//                        let searchPredicate = phoneOtp.submitCodePredicates[i];
//                        let submitOtpCodeDomObject = await findFirstElement(searchPredicate, await getContinuationFrameId());
//                        if (submitOtpCodeDomObject != null) {
//                            const command =
//                            {
//                                tabId: launchLoginTabId,
//                                domCssSelector: submitOtpCodeDomObject.domCssSelector,
//                                frameId: await getContinuationFrameId()
//                            };
//                            await chrome.runtime.sendMessage(extensionId, { clickElement: command });
//                            console.log('phone otp submitted');
//                            break;
//                        }
//                    }
//                }
//            }
//        }
//        if (request.closeCallerTab) {
//            console.log("WOULD HAVE CLOSED");
//            //const command = {
//            //    getActiveTabId: {},
//            //};
//            //const activeTabId = await chrome.runtime.sendMessage(extensionId, command);
//            //await chrome.runtime.sendMessage(extensionId, {
//            //    removeTab: { tabId: activeTabId },
//            //});
//        }
//        async function findFirstElement(searchPredicate: CssSearchPredicateDto, frameId: number | undefined) {
//            const command =
//            {
//                findElements:
//                {
//                    tabId: launchLoginTabId,
//                    primaryCssSelector: searchPredicate.cssSelector,
//                    childCssSelector: searchPredicate.targetChildCssSelectorFragment,
//                    frameId: frameId
//                }
//            };
//            const elements = await chrome.runtime.sendMessage(extensionId, command);
//            let textOrValue = searchPredicate.textOrValuePredicate;
//            let cssSelector = searchPredicate.cssSelector;
//            let searchMode = searchPredicate.searchModes;
//            for (let j = 0; j < elements.length; j++) {
//                const domObject = elements[j];
//                if (!domObject.checkVisibilityResult) {
//                    continue;
//                }
//                var newHTMLDocument = document.implementation.createHTMLDocument('sandbox');
//                var element = newHTMLDocument.createElement('div') as HTMLElement;
//                element.innerHTML = domObject.outerHTML;
//                const elementTextToEvaluate = getElementTextToEvaluate(element).trim().toLowerCase();
//                if (textOrValue) {
//                    if (!search(searchMode, elementTextToEvaluate, textOrValue)) {
//                        continue;
//                    }
//                }
//                return domObject;
//            }
//            function getElementTextToEvaluate(element) {
//                if (element.nodeName == 'INPUT') {
//                    return element.value;
//                }
//                else {
//                    return element.innerText;
//                }
//            }
//            function search(searchMode, elementTextToEvaluate, textOrValue) {
//                if (searchMode === 'contains') {
//                    if (elementTextToEvaluate.indexOf(textOrValue.toLowerCase()) !== -1) {
//                        return true;
//                    }
//                }
//                else {
//                    if (elementTextToEvaluate === textOrValue.toLowerCase()) {
//                        return true;
//                    }
//                }
//                return false;
//            }
//        }
//    }
//}
//const _ztService = new zerotrustService();
globalWindow.zerotrust =
    {
        cryptoHelper: new cryptoHelper(),
        totp: TOTP,
        //autoLogin: async (extensionId, parameters: AutoLoginJsParameters) => {
        //    await _ztService.doAutoLogin(extensionId, parameters);
        //},
        //snapshot: async (crExtId, parameters) => {
        //    const response = await chrome.runtime.sendMessage(crExtId, { snapshot: parameters });
        //    console.log(response);
        //    return response;
        //},
    };
