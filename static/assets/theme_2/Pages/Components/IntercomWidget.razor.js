export function authenticateIntercomForUser(appId, userId, username, email, hash) {
    window.Intercom('boot', {
        app_id: appId,
        user_id: userId,
        name: username,
        email: email,
        user_hash: hash
    });
}

export function logOutClearCache(appId) {
    window.Intercom('shutdown');
    window.Intercom('boot', {
        app_id: appId,
    });
}