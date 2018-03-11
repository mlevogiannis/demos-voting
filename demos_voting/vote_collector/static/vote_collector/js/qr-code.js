// Using the new mediaDevices.getUserMedia() API in older browsers.
// https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia#Using_the_new_API_in_older_browsers

// Older browsers might not implement mediaDevices at all, so we set an empty object first
if (navigator.mediaDevices === undefined) {
    navigator.mediaDevices = {};
}

// Some browsers partially implement mediaDevices. We can't just assign an object
// with getUserMedia as it would overwrite existing properties.
// Here, we will just add the getUserMedia property if it's missing.
if (navigator.mediaDevices.getUserMedia === undefined) {
    navigator.mediaDevices.getUserMedia = function(constraints) {
        // First get ahold of the legacy getUserMedia, if present
        var getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
        // Some browsers just don't implement it - return a rejected promise with an error
        // to keep a consistent interface.
        if (!getUserMedia) {
            return Promise.reject(new Error(unsupportedBrowserMessage));
        }
        // Otherwise, wrap the call to the old navigator.getUserMedia with a Promise.
        return new Promise(function(resolve, reject) {
            getUserMedia.call(navigator, constraints, resolve, reject);
        });
    }
}

// ----------------------------------------------------------------------------

var video = document.querySelector('video');
var canvas = document.querySelector('canvas');
var context = canvas.getContext('2d');
var stream = null;

var constraints = {
    audio: false,
    video: {
        facingMode: 'environment',
    },
};

function captureToCanvas() {
    if (stream !== null) {
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        try {
            qrcode.decode();
        } catch (e) {
            //console.log(e);
        }
        setTimeout(captureToCanvas, 500);
    }
}


qrcode.callback = function (result) {
    var isValid = false;
    for (var i = 0, len = validUrlPrefixes.length; i < len; i++) {
        if (result.lastIndexOf(validUrlPrefixes[i], 0) == 0) {
            isValid = true;
            break;
        }
    }
    if (isValid) {
        video.pause();
        stream.getVideoTracks().forEach(function(videoTrack) {
            videoTrack.stop();
        });
        stream = null;
        window.location.href = result;
    }
}

function videoSuccess(_stream) {
    var embedElement = $('video').parent('.embed-responsive');
    embedElement.removeClass('hidden');
    $('#alert-placeholder').remove();
    $(window).scrollTop(embedElement.offset().top - 10);
    stream = _stream;
    if ('srcObject' in video) {
        video.srcObject = stream;
    } else {
        video.src = window.URL.createObjectURL(stream);
    }
    canvas.width = video.offsetWidth;
    canvas.height = video.offsetHeight;
    video.play();
    captureToCanvas();
}

function videoError(error) {
    var errorMessage = null;
    switch(error.name) {
        case 'NotAllowedError':
        case 'PermissionDeniedError':
        case 'PermissionDismissedError':
            errorMessage = permissionDeniedMessage;
            break;
        case 'NotFoundError':
        case 'DevicesNotFoundError':
            errorMessage = cameraNotFoundMessage;
            break;
        default:
            errorMessage = error.message;
            break;
    }
    var messageAlert = $('<div>', {id: 'alert', class: 'alert alert-danger', role: 'alert'}).text(errorMessage);
    $('#alert').replaceWith(messageAlert).length || messageAlert.appendTo('#alert-placeholder');
}

function scanQRCode() {
    navigator.mediaDevices.getUserMedia(constraints).then(videoSuccess).catch(videoError);
    var messageAlert = $('<div>', {id: 'alert', class: 'alert alert-warning', role: 'alert'}).text(requestPermissionMessage);
    $('#alert').replaceWith(messageAlert).length || messageAlert.appendTo('#alert-placeholder');
}

$('#instructions button').click(function (e) {
    $(this).closest('#instructions').addClass('hidden');
    scanQRCode();
});
