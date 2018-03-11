$('#ballot-audit').find('.btn[data-ballot-fields], .btn[data-part-fields], .btn[data-question-fields], .btn[data-option-fields]').click(function (e) {
    jsonModalShowLoading();
    var button = $(this);
    function successCallback() {
        jsonModalSetContent(button.data('data'));
        jsonModalShowContent();
    }
    if (button.data('data') == undefined) {
        populateData(button, successCallback, jsonModalShowError);
    } else {
        successCallback();
    }
});

function populateData(element, successCallback, errorCallback) {
    var partElement = element.closest('[data-part-tag]');
    var questionElement = element.closest('[data-question-index]');
    var optionElement = element.closest('[data-option-index]');

    var queryString = '?fields=';
    if (partElement.length) {
        queryString += 'parts(';
        if (questionElement.length) {
            queryString += 'questions(';
            if (optionElement.length) {
                var fields = element.data('optionFields').split(' ');
                queryString += 'options(' + fields.join(',') + ')';
            } else {
                var fields = element.data('questionFields').split(' ');
                queryString += fields.join(',');
            }
            queryString += ')';
        } else {
            var fields = element.data('partFields').split(' ');
            queryString += fields.join(',');
        }
        queryString += ')';
    } else {
        var fields = element.data('ballotFields').split(' ');
        queryString += fields.join(',');
    }

    $.ajax({
        url: ballotApiUrl + queryString,
        success: function(ballot, textStatus, jqXHR) {
            var ballotElement = $('#ballot-audit');
            if ('parts' in ballot) {
                for (var p = 0; p < ballot.parts.length; p++) {
                    var part = ballot.parts[p];
                    var partElement = ballotElement.find('[data-part-tag="' + ['A', 'B'][p] + '"]');
                    if ('questions' in part) {
                        for (var q = 0; q < part.questions.length; q++) {
                            var question = part.questions[q];
                            var questionElement = partElement.find('[data-question-index="' + q + '"]');
                            if ('options' in question) {
                                for (var o = 0; o < question.options.length; o++) {
                                    var option = question.options[o];
                                    var optionElement = questionElement.find('[data-option-index="' + o + '"]');
                                    optionElement.find('[data-option-fields="' + fields.join(' ') + '"]').data('data', option);
                                }
                            } else {
                                questionElement.find('[data-question-fields="' + fields.join(' ') + '"]').data('data', question);
                            }
                        }
                    } else {
                        partElement.find('[data-part-fields="' + fields.join(' ') + '"]').data('data', part);
                    }
                }
            } else {
                ballotElement.find('[data-ballot-fields="' + fields.join(' ') + '"]').data('data', ballot);
            }
            successCallback();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            errorCallback();
        }
    });
}

var jsonModal = $('#json-modal');
var jsonModalLoading = $('#json-modal-loading');
var jsonModalError = $('#json-modal-error');
var jsonModalContent = $('#json-modal-content');
var jsonModalCopyToClipboard = $('#json-modal-copy-to-clipboard');

new ClipboardJS('#json-modal-copy-to-clipboard');

function jsonModalShowLoading() {
    jsonModalError.add(jsonModalContent).addClass('hidden');
    jsonModalLoading.removeClass('hidden');
    jsonModalCopyToClipboard.prop('disabled', true);
    if (!jsonModal.hasClass('in')) {
        jsonModal.modal('show');
    }
}

function jsonModalShowError() {
    jsonModalLoading.add(jsonModalContent).addClass('hidden');
    jsonModalError.removeClass('hidden');
    jsonModalCopyToClipboard.prop('disabled', true);
    if (!jsonModal.hasClass('in')) {
        jsonModal.modal('show');
    }
}

function jsonModalShowContent() {
    jsonModalLoading.add(jsonModalError).addClass('hidden');
    jsonModalContent.removeClass('hidden');
    jsonModalCopyToClipboard.prop('disabled', false);
    if (!jsonModal.hasClass('in')) {
        jsonModal.modal('show');
    }
}

function jsonModalSetContent(data) {
    jsonModalContent.text(JSON.stringify(data, null, 4));
}

jsonModal.on('hidden.bs.modal', function (e) {
    jsonModalContent.empty();
});
