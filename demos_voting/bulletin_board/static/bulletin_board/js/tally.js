function validateSecretKey() {
    var input = $('#secret-key-input');
    var secretKey = input.val().trim();
    var errorMessage = '';
    if (secretKey) {
        input.val(secretKey);
        try {
            sjcl.codec.base64.toBits(secretKey);
        } catch (e) {
            errorMessage = invalidSecretKeyFormatMessage;
        }
    } else {
        errorMessage = requiredFieldMessage;
        input.val('');
    }
    textInputSetErrorMessage(input, errorMessage);
    return !errorMessage;
}

function textInputSetErrorMessage(input, errorMessage) {
    input.data('isValid', !errorMessage);
    input.parent('.form-group').toggleClass('has-error', !!errorMessage);
    var heightBefore = $(document).height();
    input.siblings('.help-block').text(errorMessage);
    var heightAfter = $(document).height();
    // Scroll the page so that any buttons at the bottom will stay at the same
    // position.
    $(window).scrollTop($(window).scrollTop() + (heightAfter - heightBefore));
}

$('#secret-key-input').change(validateSecretKey);

$('#secret-key-form').on('submit', function(e) {
    e.preventDefault();
    var secretKeyInputIsValid = $('#secret-key-input').data('isValid');
    if (secretKeyInputIsValid === undefined) {
        secretKeyInputIsValid = validateSecretKey();
    }
    if (secretKeyInputIsValid) {
        $('#tally-nav a[href="#worker-tab"]').tab('show');
    }
});

$('#tally-nav a[href="#worker-tab"]').on('shown.bs.tab', function (e) {
    startWorkers($('#secret-key-input').val());
})

function incrementProgressBar(value) {
    var progressBar = $('#worker-tab .progress-bar');
    var progress = parseInt(progressBar.data('progress') || 0) + value;
    progressBar.data('progress' , progress);
    var percent = ((progress / castBallotCount) * 100) || 1;
    progressBar.css('width', percent + '%').attr('aria-valuenow', percent);
}

function showSuccess() {
    $('#tally-nav a[href="#success-tab"]').tab('show');
}

function showError(msg) {
    $('#tally-tab-content').addClass('hidden');
    var errorElement = $('#tally-error');
    $('<div>', {class: 'alert alert-danger', role: 'alert'}).text(unknownErrorMessage).appendTo(errorElement.children('.alert-placeholder'));
    errorElement.removeClass('hidden');
}

var activeWorkerCount = 0;
var hasError = false;
var electionResult = null;

function startWorkers(secretKey) {
    if (castBallotCount == 0) {
        electionResult = {questions: []};
        for (var i = 0; i < questionCount; i++) {
            electionResult.questions.push({tally_decommitment: []});
        }
        sendElectionResult();
        return;
    }
    var workers = [];
    var hardwareConcurrency = navigator.hardwareConcurrency || 1;
    var q = Math.floor(castBallotCount / hardwareConcurrency);
    var r = castBallotCount % hardwareConcurrency;
    var workerRanges = []
    for (var i = 0; i < hardwareConcurrency; i++) {
        var rangeStart = q * i + Math.min(i, r);
        var rangeStop = q * (i + 1) + Math.min((i + 1), r);
        if (rangeStart >= rangeStop) {
            break;
        }
        workerRanges.push({rangeStart: rangeStart, rangeStop: rangeStop});
    }
    // Initialize the workers.
    for (var i = 0; i < workerRanges.length; i++) {
        var worker = new Worker(workerScriptUrl);
        worker.onmessage = function (e) {
            if (hasError) {
                return;
            }
            switch (e.data.type) {
                case 'progress':
                    incrementProgressBar(e.data.value);
                    break;
                case 'result':
                    if (electionResult === null) {  // set result
                        electionResult = e.data.value;
                    } else {  // merge result
                        for (var q = 0; q < electionResult.questions.length; q++) {
                            var tallyDecommitment = electionResult.questions[q].tally_decommitment;
                            var newTallyDecommitment = e.data.value.questions[q].tally_decommitment;
                            if (tallyDecommitment.length == 0 && newTallyDecommitment.length != 0) {
                                for (var j = 0; j < newTallyDecommitment.length; j++) {
                                    tallyDecommitment.push(sjcl.codec.base64.fromBits(new sjcl.bn(0)));
                                }
                            }
                            if (tallyDecommitment.length != 0 && newTallyDecommitment.length == 0) {
                                for (var j = 0; j < tallyDecommitment.length; j++) {
                                    newTallyDecommitment.push(sjcl.codec.base64.fromBits(new sjcl.bn(0)));
                                }
                            }
                            for (var o = 0; o < tallyDecommitment.length; o++) {
                                var a = sjcl.bn.fromBits(sjcl.codec.base64.toBits(tallyDecommitment[o]));
                                var b = sjcl.bn.fromBits(sjcl.codec.base64.toBits(newTallyDecommitment[o]));
                                tallyDecommitment[o] = sjcl.codec.base64.fromBits(a.add(b).toBits());
                            }
                        }
                    }
                    // If this was the last worker, send the result to the server.
                    activeWorkerCount--;
                    if (activeWorkerCount == 0) {
                        sendElectionResult();
                    }
                    break;
            };
        };
        worker.onerror = function (e) {
            if (hasError) {
                return;
            }
            for (var i = 0; i < workers.length; i++) {
                workers[i].terminate();
            }
            hasError = true;
            showError();
        };
        workers.push(worker);
    }
    // Start the workers.
    activeWorkerCount = workerRanges.length;
    for (var i = 0; i < workerRanges.length; i++) {
        var range = workerRanges[i];
        var worker = workers[i];
        worker.postMessage({
            electionUrl: electionUrl,
            secretKey: secretKey,
            rangeStart: range.rangeStart,  // inclusive
            rangeStop: range.rangeStop,  // exclusive
            csrfToken: csrfToken,
            sjclScriptUrls: sjclScriptUrls,
        });
    }
}

function sendElectionResult() {
    var xhr = new XMLHttpRequest();
    xhr.open('PATCH', electionUrl);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-CSRFToken', csrfToken);
    xhr.onload = function () {
        if (xhr.status == 200) {
            showSuccess();
        } else {
            hasError = true;
            showError();
        }
    }
    xhr.send(JSON.stringify(electionResult));
}
