function validateSerialNumber() {
    var input = $('#serial-number-input');
    var serialNumber = input.val().trim();
    var errorMessage = '';
    if (serialNumber) {
        if (!(/^[0-9]+$/.test(serialNumber)) || serialNumber < 100 || serialNumber > 100 + ballotCount - 1) {
            errorMessage = invalidSerialNumberMessage;
        } else {
            input.val(serialNumber);
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

$('#serial-number-form').on('submit', function(e) {
    e.preventDefault();
    if (validateSerialNumber()) {
        window.location = ballotsUrl + $('#serial-number-input').val();
    }
});

$('#election-audit').find('.btn[data-election-fields], .btn[data-question-fields], .btn[data-option-fields]').click(function (e) {
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
    var questionElement = element.closest('[data-question-index]');
    var optionElement = element.closest('[data-option-index]');

    var queryString = '?fields=';
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
        var fields = element.data('electionFields').split(' ');
        queryString += fields.join(',');
    }

    $.ajax({
        url: electionApiUrl + queryString,
        success: function(election, textStatus, jqXHR) {
            var electionElement = $('#election-audit');
            if ('questions' in election) {
                for (var q = 0; q < election.questions.length; q++) {
                    var question = election.questions[q];
                    var questionElement = electionElement.find('[data-question-index="' + q + '"]');
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
                electionElement.find('[data-election-fields="' + fields.join(' ') + '"]').data('data', election);
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

var clipboard = new ClipboardJS('#json-modal-copy-to-clipboard');

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

var candidatesRowCollapse = $('.candidates-row .collapse');

candidatesRowCollapse.on('show.bs.collapse', function () {
    var candidatesRow = $(this).closest('tr.candidates-row');
    var partyRow = $('tr.party-row[data-toggle="collapse"][data-target="#' + $(this).attr('id') + '"]');
    candidatesRow.removeClass('hidden');
    partyRow.find("td.candidates > .fa").removeClass('fa-chevron-right').addClass('fa-chevron-down');
});

candidatesRowCollapse.on('hide.bs.collapse', function () {
    var partyRow = $('tr.party-row[data-toggle="collapse"][data-target="#' + $(this).attr('id') + '"]');
    partyRow.find("td.candidates > .fa").removeClass('fa-chevron-down').addClass('fa-chevron-right');
});

candidatesRowCollapse.on('hidden.bs.collapse', function () {
    var candidatesRow = $(this).closest('tr.candidates-row');
    candidatesRow.addClass('hidden');
});
