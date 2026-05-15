export class cryptoHelper {
    constructor() {
    }
    async derivatePBKDF2(passwordArr, saltArr, iterations, hashMode = 'SHA-512') {
        const passwordKey = await crypto.subtle.importKey('raw', passwordArr, 'PBKDF2', false, ['deriveBits']);
        const derivedKey = await crypto.subtle.deriveBits({
            name: 'PBKDF2',
            salt: saltArr,
            iterations: iterations,
            hash: hashMode
        }, passwordKey, 256);
        return new Uint8Array(derivedKey);
    }
    async aesGcmEncrypt(plainTextArr, keyArr) {
        // Generate a random initialization vector (IV)
        const iv = crypto.getRandomValues(new Uint8Array(12)); // 12 bytes is the recommended length for GCM
        // Import the key
        const cryptoKey = await crypto.subtle.importKey('raw', keyArr, { name: 'AES-GCM' }, false, ['encrypt']);
        // Encrypt the data
        const encryptedBuffer = await crypto.subtle.encrypt({
            name: 'AES-GCM',
            iv: iv,
            tagLength: 128
        }, cryptoKey, plainTextArr);
        var encryptedArr = new Uint8Array(encryptedBuffer);
        const result = {
            cipherText: this.byteArrayToBase64(encryptedArr.slice(0, encryptedArr.length - 128 / 8)),
            iv: this.byteArrayToBase64(new Uint8Array(iv)),
            tag: this.byteArrayToBase64(encryptedArr.slice(encryptedArr.length - 128 / 8))
        };
        return result;
    }
    async aesGcmDecryptSecuredCipherString(securedCipherString, keyArr) {
        if (typeof securedCipherString === "string") {
            const split = securedCipherString.split(',');
            return await this.aesGcmDecrypt(split[0], split[1], split[2], keyArr);
        }
        else {
            return await this.aesGcmDecrypt(securedCipherString.iv, securedCipherString.cipherText, securedCipherString.tag, keyArr);
        }
    }
    //padPlainText(src: string, len: number = 14): string {
    //    //padding for short cipher strings
    //    if (src.length <= len) {
    //        const padding = len - src.length;
    //        const zeroPad = (num: number, places: number): string => String(num).padStart(places, '0')
    //        const paddedValue = zeroPad(padding, 2);
    //        src = paddedValue + src;
    //        for (let i = 0; i < padding; i++) {
    //            src += 0;
    //        }
    //    }
    //    else {
    //        src = '00' + src;
    //    }
    //    return src;
    //}
    //unpadPlainText(src: string, pad: boolean): string {
    //    if (!pad) {
    //        return src;
    //    }
    //    var padding = parseInt(src.slice(0, 2));
    //    var actualPlainText = src.slice(2, src.length - padding);
    //    return actualPlainText;
    //}
    async aesGcmBulkDecryptSecuredCipherStrings(cipherStrings, keyArr) {
        let strings = [];
        for (const cipherString of cipherStrings) {
            if (cipherString != null) {
                let plainTextArr = await this.aesGcmDecryptSecuredCipherString(cipherString, keyArr);
                strings.push(plainTextArr);
            }
            else {
                strings.push(new Uint8Array(0));
            }
        }
        //await cipherStrings.forEach(async x => {
        //    if (x != null) {
        //        let plainTextArr = await this.aesGcmDecryptSecuredCipherString(x, keyArr);
        //        strings.push(plainTextArr);
        //    }
        //    else {
        //        strings.push(new Uint8Array(0));
        //    }
        //})
        return strings;
    }
    async aesGcmDecrypt(iv64, cipherText64, tag64, keyArr) {
        // Convert the base64 encrypted data to a byte array
        const ciphertextArr = this.base64ToByteArray(cipherText64);
        const ivArr = this.base64ToByteArray(iv64);
        const tagArr = this.base64ToByteArray(tag64);
        var combinedCipherTag = new Uint8Array(ciphertextArr.length + tagArr.length);
        combinedCipherTag.set(ciphertextArr);
        combinedCipherTag.set(tagArr, ciphertextArr.length);
        // Import the key
        const cryptoKey = await crypto.subtle.importKey('raw', keyArr, { name: 'AES-GCM' }, false, ['decrypt']);
        // Decrypt the data
        const decryptedBuffer = await crypto.subtle.decrypt({
            name: 'AES-GCM',
            iv: ivArr
        }, cryptoKey, combinedCipherTag);
        var decryptedArr = new Uint8Array(decryptedBuffer);
        return decryptedArr;
    }
    async generateRsaKeyPair(length = 2048) {
        const rsaOptions = {
            name: 'RSA-OAEP',
            modulusLength: length,
            publicExponent: new Uint8Array([0x01, 0x00, 0x01]), // 65537
            hash: { name: 'SHA-1' },
        };
        try {
            const keyPair = await crypto.subtle.generateKey(rsaOptions, true, ['encrypt', 'decrypt']);
            const publicKey = await crypto.subtle.exportKey('spki', keyPair.publicKey);
            const privateKey = await crypto.subtle.exportKey('pkcs8', keyPair.privateKey);
            return {
                publicKeyArr: new Uint8Array(publicKey),
                privateKeyArr: new Uint8Array(privateKey),
            };
        }
        catch (err) {
            console.error(err);
            throw err;
        }
    }
    async generateAesKey(length = 256) {
        // Generate AES key
        const aesKey = await crypto.subtle.generateKey({
            name: "AES-GCM",
            length: length, // Length can be 128, 192, or 256 bits
        }, true, // Extractable
        ["encrypt", "decrypt"] // Key usages
        );
        // Export key material to ArrayBuffer
        const keyMaterial = await crypto.subtle.exportKey('raw', aesKey);
        // Convert ArrayBuffer to Uint8Array
        const keyBytes = new Uint8Array(keyMaterial);
        return keyBytes;
    }
    async rsaEncrypt(plaintextByteArr, spkiPubKey) {
        const spkiArr = this.base64ToByteArray(spkiPubKey);
        // Import the public key
        const publicKey = await crypto.subtle.importKey("spki", spkiArr, {
            name: "RSA-OAEP",
            hash: { name: "SHA-256" }
        }, true, ["encrypt"]);
        // Encrypt the plaintext
        const encryptedData = await crypto.subtle.encrypt({
            name: "RSA-OAEP"
        }, publicKey, plaintextByteArr);
        return new Uint8Array(encryptedData);
    }
    async rsaDecrypt(cipherTextArr, privateKeyArr) {
        // Import the private key
        const decryptionKey = await crypto.subtle.importKey("pkcs8", // PKCS #8 format for private keys
        privateKeyArr, {
            name: "RSA-OAEP",
            hash: { name: "SHA-256" }
        }, true, // Extractable
        ["decrypt"] // Key usages
        );
        // Decrypt the ciphertext
        const decryptedData = await crypto.subtle.decrypt({
            name: "RSA-OAEP"
        }, decryptionKey, cipherTextArr);
        return new Uint8Array(decryptedData);
    }
    textToByteArray(text) {
        const encoder = new TextEncoder();
        return encoder.encode(text);
    }
    byteArrayToText(byteArray) {
        const decoder = new TextDecoder();
        return decoder.decode(byteArray);
    }
    base64ToByteArray(base64) {
        return Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    }
    byteArrayToBase64(byteArray) {
        return btoa(String.fromCharCode(...byteArray));
    }
}
