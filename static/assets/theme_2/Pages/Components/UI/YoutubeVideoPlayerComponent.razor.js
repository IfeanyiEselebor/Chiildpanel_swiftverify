/**
 * elementId, element
 * @type {Object.<string, Object>}
 */
var youtubeVideoComponents = {};
let _scriptLoaded = false;

export async function loadScript() {
    return new Promise((resolve, reject) => {
        if (!_scriptLoaded) {
            _scriptLoaded = true;
            var script = document.createElement("script");
            script.src = 'https://www.youtube.com/iframe_api';

            script.onload = () => {
                window.onYouTubeIframeAPIReady = () => {
                    resolve();
                };
            }
            document.head.appendChild(script);
        } else {
            resolve();
        }
    });
}

/*
 * Initialize the video
 * Check the different events here: https://developers.google.com/youtube/iframe_api_reference#Events
 * Params:
 *   (string) youtubeVideoId: The youtube video's ID from it's url
 *   (string) elementId: Should be auto-generated from YoutubeVideoPlayerComponent.razor.cs, this is the div
 *      youtube's api will replace with the iframe
 *   (string) elementLoaderId: Should be auto-generated from YoutubeVideoPlayerComponent.razor.cs, this is a loading
 *      indicator that will be hidden when the iframe is ready
 */
export async function initializeVideoIframe(youtubeVideoId, elementId, elementLoaderId) {
    if (window.YT && window.YT.Player) {
        youtubeVideoComponents[elementId] = new YT.Player(elementId, {
            videoId: youtubeVideoId,
            events: {
                'onReady': (event) => {
                    let loader = document.querySelector("#" + elementLoaderId);
                    if (loader) {
                        loader.classList.add("hidden");
                    }
                },
            }
        });
    } else {
        console.error('YouTube API is not loaded.');
    }
}

export async function stopVideoPlayback(elementId) {
    let player = youtubeVideoComponents[elementId];
    if (player) {
        player.stopVideo();
    }
}