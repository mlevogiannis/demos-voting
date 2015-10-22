window.URL = window.URL || window.webkitURL ;

navigator.mediaDevices = navigator.mediaDevices || ((navigator.mozGetUserMedia || navigator.webkitGetUserMedia) ? {
    getUserMedia: function(c) {
        return new Promise(function(y, n) {
            (navigator.mozGetUserMedia || navigator.webkitGetUserMedia).call(navigator, c, y, n);
        });
    }
} : null);

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    
    $("#qrcode-alert").removeClass("hidden");
    $("#qrcode > :not(#qrcode-alert)").addClass("hidden");
    
    var videoElem = $("#qr-video");
    var video = videoElem[0];
    
    var canvasElem = $("#qr-canvas");
    var canvas = canvasElem[0];
    
    var stream = null;
    var context = canvas.getContext("2d");
    var constraints = { video: true, audio: false };
    
    qrcode.callback = function(data) {
        
        video.pause();
        stream.stop();
        
        var qrcode_modal = $("#qrcode-modal");
        
        qrcode_modal.find("a").attr("href", data);
        qrcode_modal.find("code").text(data);
        qrcode_modal.modal("show");
        
        window.location.href = data;
    };
    
    function canvasDecode() {
        
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        try { qrcode.decode(); }
        catch (e) { setTimeout(canvasDecode, 250); }
    }
    
    navigator.mediaDevices.getUserMedia(constraints).then(function(stream_) {
        
        stream = stream_;
        
        $("#qrcode-frame").removeClass("hidden");
        $("#qrcode > :not(#qrcode-frame)").addClass("hidden");
        
        canvas.width = videoElem.width();
        canvas.height = videoElem.height();
        
        video.src = window.URL ? window.URL.createObjectURL(stream) : stream;
        video.play();
        
        canvasDecode();
        
    }).catch(function(err) {
        
        $("#qrcode-error").removeClass("hidden");
        $("#qrcode > :not(#qrcode-error)").addClass("hidden");
        
        var errno;
        
        switch(err.name) {
            
            case "PermissionDeniedError":
                errno = $("#qrcode-denied");
                break;
            
            case "NotFoundError":
            case "DevicesNotFoundError":
                errno = $("#qrcode-not-found");
                break;
            
            default:
                errno = $("#qrcode-other-error");
                var msg = errno.children("p").text();
                msg.substr(0, msg.indexOf(":"));
                errno.children("p").text(msg + " " + err.name + (err.message ? ": " + err.message : ""));
                break;
        }
        
        errno.removeClass("hidden");
    });
}
else {
        
    $("#qrcode-error").removeClass("hidden");
    $("#qrcode > :not(#qrcode-error)").addClass("hidden");
    
    $("#qrcode-unsupported").removeClass("hidden");
}

