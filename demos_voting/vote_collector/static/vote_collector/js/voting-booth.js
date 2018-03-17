$(document).on('keypress', '#voting-booth-form', function (e) {
    // Do not submit the form on enter key press.
    return e.keyCode != 13;
});

$('#voting-booth-nav a[data-toggle="tab"]').click(function (e) {
    // Prevent clicking on disabled links.
    if ($(this).parent('li').hasClass('disabled')) {
        e.preventDefault();
        return false;
    }
});

$('#voting-booth-nav a[data-toggle="tab"]').on('show.bs.tab', function (e) {
    // Enable the tab to be shown.
    var tab = $(e.target).parent('li').removeClass('disabled');
    if (tab.is(':last-child')) {
        // If it is the last tab then disable all previous tabs.
        tab.prevAll().addClass('disabled');
    } else {
        // Otherwise disable all the tabs after it.
        tab.nextAll().addClass('disabled');
    }
});

$('#voting-booth-nav a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    // Scroll to the top of the page when a new tab is shown.
    var element = $(e.target).closest('.nav');
    if (!element.is(':visible')) {
        element = $($(e.target).attr('href')).parent('.tab-content');
    }
    $(window).scrollTop(element.offset().top - 10);
});

$('#voting-booth-nav a[href="#vote-tab"]').on('show.bs.tab', function (e) {
    window.onbeforeunload = function(e) {
        e.returnValue = undefined;
        return undefined;
    };
});

$('#voting-booth-nav a[href="#verify-receipts-tab"]').on('show.bs.tab', function (e) {
    window.onbeforeunload = null;
});

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

function generatePermutations() {
    permutations = [];  // global var
    for (var index = 0; index < optionCounts.length; index++) {
        permutations.push(generatePermutation(index));
    }
}

if (typeof voteCodeTypeIsShort !== 'undefined' && typeof securityCodeLength !== 'undefined') {
    if(voteCodeTypeIsShort && securityCodeLength == null) {
        generatePermutations();
    }
}

function validateSecurityCode() {
    var input = $('#security-code-input');
    securityCode = input.val().trim();  // global var
    var errorMessage = '';
    if (securityCode) {
        if (!(/^[0-9]+$/.test(securityCode)) || securityCode.length != securityCodeLength || !validateCheckCharacter(securityCode, '0123456789')) {
            errorMessage = invalidSecurityCodeFormatMessage;
        } else {
            input.val(getSecurityCodeDisplay(securityCode));
            try {
                // Generate the questions' permutations. An exception will be
                // raised if a permutation encoded in the security code is not
                // in range from from 0 to factorial(optionCount) - 1.
                generatePermutations();
            } catch (e) {
              errorMessage = invalidSecurityCodeFormatMessage;
            }
        }
    } else {
        errorMessage = requiredFieldMessage;
        input.val('');
    }
    textInputSetErrorMessage(input, errorMessage);
    return !errorMessage;
}

function validateCredential() {
    var input = $('#credential-input');
    credential = input.val().trim();  // global var
    var errorMessage = '';
    if (credential) {
        if (!base32.validate(credential)) {
            errorMessage = invalidCredentialFormatMessage;
        } else {
            credential = base32.normalize(credential);
            if (credential.length != credentialLength) {
              errorMessage = invalidCredentialFormatMessage;
            } else {
                credential = base32.hyphenate(credential, 4);
            }
        }
        if (!errorMessage) {
            input.val(getCredentialDisplay(credential));
        }
    } else {
        errorMessage = requiredFieldMessage;
        input.val('');
    }
    textInputSetErrorMessage(input, errorMessage);
    return !errorMessage;
}

$('#security-code-input').change(validateSecurityCode);
$('#credential-input').change(validateCredential);

$('#security-code-or-credential-form').on('submit', function(e) {
    e.preventDefault();
    var isValid = false;
    if (voteCodeTypeIsShort) {
        isValid = $('#security-code-input').data('isValid');
        if (isValid === undefined) {
            isValid = validateSecurityCode();
        }
    } else if (voteCodeTypeIsLong) {
        isValid = $('#credential-input').data('isValid');
        if (isValid === undefined) {
            isValid = validateCredential();
        }
    }
    if (isValid) {
        if ($('.checkbox-ui:first').hasClass('hidden')) {
            // Reset the questions.
            $('.checkbox-ui .question').each(function (index, element) {
                resetQuestionCheckBoxUI($(this));
            });
            // Hide the candidate question.
            if (typeIsPartyCandidate) {
                $('.checkbox-ui .question[data-index="1"]').closest('.panel').addClass('hidden');
            }
        }
        // Enable the checkbox-based voting inteface.
        $('.textinput-ui').addClass('hidden');
        $('.checkbox-ui').removeClass('hidden');
        $('#voting-booth-nav a[href="#vote-tab"]').tab('show');
    }
});

$('#select-interface-skip-button').click(function (e) {
    if ($('.textinput-ui:first').hasClass('hidden')) {
        // Reset the questions.
        $('.textinput-ui .question').each(function (index, element) {
            resetQuestionTextInputUI($(this));
        });
        // Force show the candidate question.
        if (typeIsPartyCandidate) {
            $('.checkbox-ui .question[data-index="1"]').closest('.panel').removeClass('hidden');
        }
    }
    // Enable the textinput-based voting inteface.
    $('.checkbox-ui').addClass('hidden');
    $('.textinput-ui').removeClass('hidden');
    $('#voting-booth-nav a[href="#vote-tab"]').tab('show');
});

function resetQuestionCheckBoxUI(question) {
    // Remove any question-level messages.
    question.siblings('.alert-placeholder').empty();
    // Reset the options' checkboxes.
    var options = question.find('input[type="checkbox"].option');
    options.prop('checked', false);
    options.prop('disabled', false);
    options.parent('label').removeClass('disabled');
    if (typeIsPartyCandidate) {
        // Hide any enabled candidate groups.
        question.find('.candidate-group').addClass('hidden');
        // Disable the candidate question.
        if (parseInt(question.data('index')) == 0) {
            $('.checkbox-ui .question[data-index="1"]').closest('.panel').addClass('hidden');
        }
    }
}

function resetQuestionTextInputUI(question) {
    // Remove any question-level messages.
    question.siblings('.alert-placeholder').empty();
    // Reset the options' text inputs.
    var options = question.find('input[type="text"].option');
    textInputSetErrorMessage(options, '');
    options.val('');
    options.removeData(['isValid', 'index', 'voteCode']);
}

function clearQuestionErrors(question) {
    question.siblings('.alert-placeholder').children('.alert').remove('.alert-danger');
}

function validateQuestionCheckBoxUI(question) {
    clearQuestionErrors(question);
    // Skip validation if their is no minimum selection count.
    var minSelectionCount = parseInt(question.data('minSelectionCount'));
    if (minSelectionCount == 0 || typeIsPartyCandidate) {
        return true;
    }
    // Validate the number of selected options.
    var isValid = (question.find('input[type="checkbox"]:checked.option').length >= minSelectionCount);
    if (!isValid) {
        var alertPlaceholder = question.siblings('.alert-placeholder');
        $('<div>', {class: 'alert alert-danger', role: 'alert'}).text(minSelectionCountMessage).appendTo(alertPlaceholder);
    }
    return isValid;
}

function validateQuestionTextInputUI(question) {
    clearQuestionErrors(question);
    // Skip validation unless all non-empty vote-codes are valid.
    var options = question.find('input[type="text"].option');
    if (options.filter(function () { return ($(this).data('isValid') == false) }).length > 0) {
        return false;
    }
    // Validate the number of entered vote-codes.
    var minSelectionCount = parseInt(question.data('minSelectionCount'));
    var isValid = (options.filter(function () { return this.value.length > 0 }).length >= minSelectionCount);
    if (!isValid) {
        var alertPlaceholder = question.siblings('.alert-placeholder');
        $('<div>', {class: 'alert alert-danger', role: 'alert'}).text(minVoteCodeCountMessage).appendTo(alertPlaceholder);
    }
    return isValid;
}

function populateVoteCodeTextInput(questionIndex, optionIndex, voteCodeIndex) {
    var voteCode = generateVoteCode(questionIndex, optionIndex);
    var option = $('.textinput-ui input[type="text"][name="question-' + questionIndex + '-option-' + voteCodeIndex + '-vote_code"].option');
    option.val(getVoteCodeDisplay(voteCode));
    option.data('isValid', true);
    option.data('index', optionIndex);
    option.data('voteCode', voteCode);
}

function populateVoteCodeTextInputs() {
    // Clear the text inputs.
    $('.textinput-ui .question').each(function (index, element) {
        resetQuestionTextInputUI($(this));
    });
    // Generate the selected options' vote-codes.
    if (typeIsQuestionOption) {
        $('.checkbox-ui .question').each(function (index, element) {
            var question = $(this);
            var questionIndex = parseInt(question.data('index'));
            question.find('input[type="checkbox"]:checked.option').each(function (index, element) {
                var option = $(this);
                var optionIndex = parseInt(option.data('index'));
                populateVoteCodeTextInput(questionIndex, optionIndex, index);
            });
        });
    } else if (typeIsPartyCandidate) {
        // Handle the party question.
        var partyQuestion = $('.checkbox-ui .question[data-index="0"]');
        var partyOptionIndex;
        var selectedPartyOption = partyQuestion.find('input[type="checkbox"]:checked.option');
        if (selectedPartyOption.length > 0) {
            partyOptionIndex = parseInt(selectedPartyOption.data('index'));
        } else {
            partyOptionIndex = parseInt(partyQuestion.data('optionCount')) - 1;  // the blank party
        }
        populateVoteCodeTextInput(0, partyOptionIndex, 0);
        // Handle the candidate question.
        var candidateQuestion = $('.checkbox-ui .question[data-index="1"]');
        var candidateGroup = candidateQuestion.find('.candidate-group[data-party-index="' + partyOptionIndex + '"]');
        var candidateOptionIndices = [];
        // Get the option indices of the selcted candidates.
        var selectedCandidateOptions = candidateGroup.find('input[type="checkbox"]:checked.option');
        selectedCandidateOptions.each(function (index, element) {
            var candidateOptionIndex = parseInt($(this).data('index'))
            candidateOptionIndices.push(candidateOptionIndex);
        });
        // Select random blank candidates and get their indices.
        var minSelectionCount = parseInt(candidateQuestion.data('minSelectionCount'));
        var requiredBlankCandidateOptionCount = minSelectionCount - selectedCandidateOptions.length;
        if (requiredBlankCandidateOptionCount > 0) {
            var blankCandidateOptionIndices = [];
            var partyOptionCount = parseInt(partyQuestion.data('optionCount'));
            var candidateOptionCount = parseInt(candidateQuestion.data('optionCount'));
            var candidateCountPerParty = Math.floor(candidateOptionCount / partyOptionCount);
            var notBlankCandidateOptionCount = candidateGroup.find('input[type="checkbox"].option:not(.blank)').length;
            for (var i = notBlankCandidateOptionCount; i < candidateCountPerParty; i++) {
                var blankCandidateOptionIndex = (partyOptionIndex * candidateCountPerParty) + i;
                blankCandidateOptionIndices.push(blankCandidateOptionIndex);
            }
            shuffleArray(blankCandidateOptionIndices);
            blankCandidateOptionIndices.splice(requiredBlankCandidateOptionCount);
            blankCandidateOptionIndices.sort(function (a, b) { return a - b });
            candidateOptionIndices = candidateOptionIndices.concat(blankCandidateOptionIndices);
        }
        // Generate the candidates' vote-codes.
        for (var i = 0, len = candidateOptionIndices.length; i < len; i++) {
            populateVoteCodeTextInput(1, candidateOptionIndices[i], i);
        }
    }
}

$('#vote-next-button').click(function (e) {
    var isValid = true;
    if (!($('.checkbox-ui:first').hasClass('hidden'))) {
        $('.checkbox-ui .question').each(function (index, element) {
            isValid &= validateQuestionCheckBoxUI($(this));
        });
        if (isValid) {
            populateVoteCodeTextInputs();
        }
    } else {
        $('.textinput-ui .question').each(function (index, element) {
            isValid &= validateQuestionTextInputUI($(this));
        });
    }
    if (isValid) {
        $('#voting-booth-nav a[href="#confirm-vote-codes-tab"]').tab('show');
    }
});

$('#vote-back-button').click(function (e) {
    $('#voting-booth-nav a[href="#select-interface-tab"]').tab('show');
});

$('#vote-reset-button').click(function (e) {
    if (!($('.checkbox-ui:first').hasClass('hidden'))) {
        $('.checkbox-ui .question').each(function (index, element) {
            resetQuestionCheckBoxUI($(this));
        });
    }
    if (!($('.textinput-ui:first').hasClass('hidden'))) {
        $('.textinput-ui .question').each(function (index, element) {
            resetQuestionTextInputUI($(this));
        });
    }
});

$('.checkbox-ui input[type="checkbox"].option').change(function (e) {
    var option = $(this);
    var question = option.closest('.question');
    // Clear question-level errors.
    clearQuestionErrors(question);
    // Validate the current number of selections.
    var currentSelectionCount = question.find('input[type="checkbox"]:checked.option').length;
    var maxSelectionCount = question.data('maxSelectionCount');
    var limitReached = currentSelectionCount >= maxSelectionCount;
    question.find('input[type="checkbox"]:not(:checked).option').each(function (index, element) {
        var otherOption = $(this);
        otherOption.prop('disabled', limitReached);
        otherOption.parent('label').toggleClass('disabled', limitReached);
    });
    var alertPlaceholder = question.siblings('.alert-placeholder');
    alertPlaceholder.children('.alert').remove('.alert-info');
    if (limitReached) {
        $('<div>', {class: 'alert alert-info', role: 'alert'}).text(maxSelectionCountMessage).appendTo(alertPlaceholder);
    }
    // Enable/disable the candidate question.
    if (typeIsPartyCandidate) {
        var questionIndex = parseInt(question.data('index'));
        if (questionIndex == 0) {
            var partyOptionChecked = option.prop('checked');
            var partyOptionIndex = parseInt(option.data('index'));
            var candidateQuestion = $('.checkbox-ui .question[data-index="1"]');
            candidateQuestion.closest('.panel').toggleClass('hidden', !partyOptionChecked);
            candidateQuestion.find('.candidate-group[data-party-index="' + partyOptionIndex + '"]').toggleClass('hidden', !partyOptionChecked);
            if (!partyOptionChecked) {
                resetQuestionCheckBoxUI(candidateQuestion);
            }
        }
    }
});

$('.textinput-ui input[type="text"].option').change(function (e) {
    // An option input element has an `isValid` (boolean) data attribute if it
    // is not empty, a `voteCode` (string) data attribute if its value's format
    // is valid and optionally an `index` (integer) data attribute if it was
    // populated by the checkbox-ui.
    var input = $(this);
    var question = input.closest('.question');
    // Clear question-level error messages.
    clearQuestionErrors(question);
    // Get the previous value (if any).
    var oldVoteCode = input.data('voteCode');
    // Validate and normalize the vote-code.
    var errorMessage = '';
    var voteCode = input.val().trim();
    if (voteCode.length > 0) {
        if (voteCodeTypeIsShort) {
            if (!(/^[1-9][0-9]*$/.test(voteCode))) {
                errorMessage = invalidVoteCodeMessage;
            } else {
                if (parseInt(voteCode) > parseInt(question.data('optionCount'))) {
                    errorMessage = invalidVoteCodeMessage;
                }
            }
        } else if (voteCodeTypeIsLong) {
            if (!base32.validate(voteCode)) {
                errorMessage = invalidVoteCodeFormatMessage;
            } else {
                voteCode = base32.normalize(voteCode);
                if (voteCode.length != voteCodeLength) {
                    errorMessage = invalidVoteCodeFormatMessage;
                }
            }
        }
        if (!errorMessage) {
            // The vote-code's format is valid at this point.
            input.val(getVoteCodeDisplay(voteCode));
            //
            if (typeIsPartyCandidate) {
                var questionIndex = parseInt(question.data('index'));
                if (questionIndex == 1) {
                    // Validate that the selected candidate options correspond
                    // to the selected party option. Only the short-vote case
                    // is handled, long vote-codes are not validated on the
                    // client side for performance reasons.
                    if (voteCodeTypeIsShort) {
                        var partyQuestion = $('.textinput-ui .question[data-index="0"]');
                        var candidateQuestion = question;
                        // Get the number of candidates per party.
                        var partyOptionCount = parseInt(partyQuestion.data('optionCount'));
                        var candidateOptionCount = parseInt(candidateQuestion.data('optionCount'));
                        var candidateCountPerParty = Math.floor(candidateOptionCount / partyOptionCount);
                        // Get the party option's index.
                        var partyVoteCode = partyQuestion.find('input[type="text"].option').data('voteCode');
                        var partyOptionIndex = shortVoteCodes[0].indexOf(partyVoteCode);
                        // Get the candidate option's index.
                        var candidateVoteCode = voteCode;
                        var candidateOptionIndex = shortVoteCodes[1].indexOf(candidateVoteCode);
                        // Validate that the candidate corresponds to the party.
                        var minCandidateOptionIndex = partyOptionIndex * candidateCountPerParty;
                        var maxCandidateOptionIndex = (partyOptionIndex + 1) * candidateCountPerParty - 1;
                        if (candidateOptionIndex < minCandidateOptionIndex || candidateOptionIndex > maxCandidateOptionIndex) {
                            errorMessage = partyCandidateCorrespondenceMessage;
                        }
                    }
                }
            }
        }
        if (!errorMessage) {
            input.data('voteCode', voteCode);
        } else {
            input.removeData('voteCode');
        }
        textInputSetErrorMessage(input, errorMessage);
    } else {
        textInputSetErrorMessage(input, '');
        input.val('');
        input.removeData(['isValid', 'voteCode']);
    }
    // Mark duplicate vote-codes.
    if (!errorMessage && voteCode.length > 0) {
        var options = question.find('input[type="text"].option').filter(function () { return $(this).data('voteCode') == voteCode });
        if (options.length > 1) {
            textInputSetErrorMessage(options, duplicateVoteCodeMessage);
        }
    }
    // Un-mark previously duplicate vote-codes.
    if (oldVoteCode !== undefined && oldVoteCode != voteCode) {
        var options = question.find('input[type="text"].option').filter(function () { return $(this).data('voteCode') == oldVoteCode });
        if (options.length == 1) {
            textInputSetErrorMessage(options, '');
        }
    }
});

function populateVoteCodeConfirmationTable() {
    var includeOptionNames = !($('.checkbox-ui:first').hasClass('hidden'));
    $('.textinput-ui .question').each(function (index, element) {
        var question = $(this);
        var questionIndex = parseInt(question.data('index'));
        var panel = $('#confirm-vote-codes-tab .panel[data-question-index="' + questionIndex + '"]');
        var tableBody = panel.find('tbody');
        // Populate the table.
        tableBody.empty();
        question.find('input[type="text"].option').each(function (index, element) {
            var option = $(this);
            var voteCode = option.val();
            if (voteCode) {
                var tableRow = $('<tr>').appendTo(tableBody);
                if (includeOptionNames) {
                    var optionIndex = parseInt(option.data('index'));
                    var optionName = $('.checkbox-ui .question[data-index="' + questionIndex + '"] input[type="checkbox"].option[data-index="' + optionIndex + '"]').siblings('.option-name').html();
                    $('<td>', {class: 'option-name'}).html(optionName).appendTo(tableRow);
                }
                $('<td>', {class: 'vote-code'}).text(voteCode).appendTo(tableRow);
                tableRow.data('voteCode', option.data('voteCode'));
            }
        });
        var isEmpty = (tableBody.children().length == 0);
        panel.find('.panel-body').toggleClass('hidden', !isEmpty);
        tableBody.parent('table').toggleClass('hidden', isEmpty);
    });
}

function populateReceiptVerificationTable(receipts) {
    $('#confirm-vote-codes-tab .panel').each(function (index, element) {
        var voteCodePanel = $(this);
        var voteCodeTableBody = voteCodePanel.find('tbody');
        var questionIndex = parseInt(voteCodePanel.data('questionIndex'));
        var receiptPanel = $('#verify-receipts-tab .panel[data-question-index="' + questionIndex + '"]');
        var receiptTableBody = receiptPanel.find('tbody');
        // Populate the table.
        voteCodeTableBody.children('tr').each(function (index, element) {
            var tableRow = $(this).clone(true).appendTo(receiptTableBody);
            var voteCode = tableRow.data('voteCode');
            var receipt = receipts[questionIndex][voteCode];
            $('<td>', {class: 'receipt'}).text(getReceiptDisplay(receipt)).appendTo(tableRow);
        });
        var isEmpty = (receiptTableBody.children().length == 0);
        receiptPanel.find('.panel-body').toggleClass('hidden', !isEmpty);
        receiptTableBody.parent('table').toggleClass('hidden', isEmpty);
    });
}

function formToObject(form) {
    var array = form.serializeArray();
    var object = {};
    for (var i = 0, len = array.length; i < len; i++) {
        var element = array[i];
        object[element['name']] = element['value'];
    }
    return object;
}

$('#voting-booth-nav a[href="#confirm-vote-codes-tab"]').on('show.bs.tab', populateVoteCodeConfirmationTable);

$('#confirm-vote-codes-submit-button').click(function (e) {
    e.preventDefault();
    $('#loading-modal').modal('show');
    var formObject = formToObject($('#voting-booth-form'));
    // Shuffle the vote-codes.
    $('.textinput-ui .question').each(function (index, element) {
        var question = $(this);
        var optionCount = parseInt(question.data('optionCount'));
        if (optionCount == 1) {
            return;
        }
        var voteCodes = [];
        var questionIndex = parseInt(question.data('index'));
        var maxSelectionCount = parseInt(question.data('maxSelectionCount'));
        for (var i = 0; i < maxSelectionCount; i++) {
            var voteCode = formObject['question-' + questionIndex  + '-option-' + i + '-vote_code'];
            if (voteCode !== undefined && voteCode.length > 0) {
                voteCodes.push(voteCode);
            }
        }
        shuffleArray(voteCodes);
        for (var i = 0; i < maxSelectionCount; i++) {
            var voteCode = i < voteCodes.length ? voteCodes[i] : '';
            formObject['question-' + questionIndex  + '-option-' + i + '-vote_code'] = voteCode;
        }
    });
    // Submit the vote to the server.
    $.ajax({
        type: 'POST',
        data: $.param(formObject),
        success: function (data, textStatus, jqXHR) {
            populateReceiptVerificationTable(data);
            $('#voting-booth-nav a[href="#verify-receipts-tab"]').tab('show');
        },
        error: function (jqXHR, textStatus, errorThrown) {
            // Disable the voting interface.
            $('#voting-booth-error').nextAll().addClass('hidden');
            // Populate the error message placeholder.
            var data = jqXHR.responseJSON;
            var alertPlaceholder = $('#voting-booth-error').children('.alert-placeholder');
            var alertMessage = $('<div>', {class: 'alert alert-danger', role: 'alert'}).appendTo(alertPlaceholder);
            $('<h4>').text(voteNotAcceptedMessage).appendTo(alertMessage);
            var errorList = $('<ul>').appendTo(alertMessage);
            if (data) {
                for (var i = 0; i < data.length; i++) {
                    $('<li>').text(data[i]).appendTo(errorList);
                }
            } else {
                $('<li>').text(unknownErrorMessage).appendTo(errorList);
            }
            $('#voting-booth-error').removeClass('hidden');
            // Scroll to the error message.
            $(window).scrollTop(alertPlaceholder.offset().top - 10);
        },
        complete: function (data, textStatus) {
            $('#loading-modal').modal('hide');
        },
    });
});

$('#confirm-vote-codes-back-button').click(function (e) {
    $('#voting-booth-nav a[href="#vote-tab"]').tab('show');
});

// ----------------------------------------------------------------------------

function getCredentialDisplay(credential) {
    return base32.hyphenate(credential, 4);
}

function getSecurityCodeDisplay(securityCode) {
    return securityCode;
}

function getVoteCodeDisplay(voteCode) {
    if (voteCodeTypeIsShort) {
        return voteCode;
    } else if (voteCodeTypeIsLong) {
        return base32.hyphenate(voteCode, 4);
    }
}

function getReceiptDisplay(receipt) {
    return receipt.slice(-receiptLength);
}

function bitLength(n) {
    // Adapted from sjcl.bn.bitLength
    var n = new sjcl.bn(n);
    n.fullReduce();
    var out = n.radix * (n.limbs.length - 1),
    b = n.limbs[n.limbs.length - 1];
    for (; b; b >>>= 1) {
        out ++;
    }
    return out;
}

function divmod(a, b) {
    // Adapted from sjcl.bn.mod
    if (!a.greaterEquals(0)) {
        throw "Negative numbers are not supported."
    }
    var b = new sjcl.bn(b).normalize();
    var q = new sjcl.bn(0);
    var r = new sjcl.bn(a).normalize();
    var ci = 0;
    for (; r.greaterEquals(b); ci++) {
        b.doubleM();
    }
    for (; ci > 0; ci--) {
        q.doubleM();
        b.halveM();
        if (r.greaterEquals(b)) {
            q.addM(1);
            r.subM(b).normalize();
        }
    }
    return [q, r.trim()];
}

function factorial(n) {
    var n = new sjcl.bn(n);
    var f = new sjcl.bn(1);
    for (var i = new sjcl.bn(2); n.greaterEquals(i); i.addM(1)) {
        f = f.mul(i);
    }
    return f;
}

function permute(inputArray, index) {
    var inputArray = inputArray.slice();
    var permCount = factorial(inputArray.length);
    if (!index.greaterEquals(0) || index.greaterEquals(permCount)) {
        throw "Invalid permutation index: " + index;
    }
    var outputArray = [];
    while (inputArray.length > 0) {
        permCount = divmod(permCount, inputArray.length)[0];
        var divmodArray = divmod(index, permCount);
        itemIndex = divmodArray[0];
        index = divmodArray[1];
        item = inputArray.splice(parseInt(itemIndex.toString(), 16), 1)[0];
        outputArray.push(item);
    }
    return outputArray
}

function generatePermutation(questionIndex) {
    if (!voteCodeTypeIsShort) {
        throw "The permutation can be generated only for elections with short vote-codes";
    }
    var optionCounts2;
    if (typeIsQuestionOption) {
        optionCounts2 = optionCounts.slice();
    } else if (typeIsPartyCandidate) {
        // For the purposes of security code generation, each candidate
        // group will be treated as a separate "question". The first
        // question corresponds to the party question, the other questions
        // correspond to the candidate groups of the candidate question.
        optionCounts2 = [optionCounts[0]].concat(Array.apply(null, Array(optionCounts[0])).map(function () {return Math.floor(optionCounts[1] / optionCounts[0])}));
    }
    // The question's permutation index.
    var p;
    // The candidate question requires special handling (the list of all
    // candidate groups' permutation indices).
    var isCandidateQuestion = typeIsPartyCandidate && questionIndex == 1;
    if (isCandidateQuestion) {
        var pArray = [];
    }
    // Generate the maximum security code length (the "ideal" length, which
    // may be greater than the actual length).
    if (securityCodeLength != null) {
        var sMax = new sjcl.bn(0);
        for (var index = 0; index < optionCounts2.length; index++) {
            var optionCount = optionCounts2[index];
            var pMax = factorial(optionCount).subM(1);
            pMax.fullReduce();
            var sMaxBitLength = bitLength(sMax);
            for (var i = 0; i < sMaxBitLength; i++) {
                pMax.doubleM();
            }
            sMax.addM(pMax);
            sMax.fullReduce();
        }
        var idealSecurityCodeLength = ('' + parseInt(sMax.toString(), 16)).length + 1;  // + 1 for the check character
    }
    if (securityCodeLength != null && securityCodeLength == idealSecurityCodeLength) {
        // Decode the security code and extract the permutation indices.
        var s = (new sjcl.bn(parseInt(securityCode.slice(0, -1)))).toBits();  // slice to remove the check character
        for (var index = 0; index < optionCounts2.length; index++) {
            var optionCount = optionCounts2[index];
            var pBitLength = bitLength(factorial(optionCount).subM(1));
            var sBitLengthRoundedUpToNearestByte = sjcl.bitArray.bitLength(s);
            p = sjcl.bn.fromBits(sjcl.bitArray.bitSlice(s, Math.max(sBitLengthRoundedUpToNearestByte - pBitLength, 0), sBitLengthRoundedUpToNearestByte));
            if (isCandidateQuestion && index >= questionIndex) {
                pArray.push(p);
            } else if (index == questionIndex) {
                break;
            }
            s = sjcl.bitArray.bitSlice(s, 0, sBitLengthRoundedUpToNearestByte - pBitLength);
        }
    } else {
        // Use randomness extraction to generate the question's permutation
        // index.
        function randomnessExtractor(questionIndex) {
            var optionCount = optionCounts2[questionIndex];
            var key = base32.toBits(credential);
            var msgArray = [serialNumber, tag, questionIndex, 'permutation'];
            if (securityCodeLength != null) {
                msgArray.push(securityCode);
            }
            var msg = msgArray.join(',');
            var hmac = new sjcl.misc.hmac(key, sjcl.hash.sha256);
            return sjcl.bn.fromBits(hmac.encrypt(msg)).mod(factorial(optionCount));
        }
        if (isCandidateQuestion) {
            for (var index = 1; index < optionCounts2.length; index++) {
                pArray.push(randomnessExtractor(index));
            }
        } else {
            p = randomnessExtractor(questionIndex);
        }
    }
    // Generate the permutation array from the permutation indices.
    if (isCandidateQuestion) {
        // Permute each candidate group's options according to the its
        // permutation index.
        var candidateCountPerParty = optionCounts2[1];
        var candidateGroups = [];
        for (var index = 0; index < pArray.length; index++) {
            p = pArray[index];
            var minOptionIndex = index * candidateCountPerParty;
            var maxOptionIndex = minOptionIndex + candidateCountPerParty - 1;
            var range = [];
            for (var i = minOptionIndex, len = maxOptionIndex + 1; i < len; i++) {
                range.push(i);
            }
            candidateGroups.push(permute(range, p));
        }
        // Permute the candidate groups according to the party question's
        // permutation. A candidate group's options can be associated with
        // their party option by comparing their indices, even when the
        // options are shuffled.
        var candidateGroups2 = [];
        for (var i = 0, len = permutations[0].length; i < len; i++) {
            candidateGroups2.push(candidateGroups[permutations[0][i]]);
        }
        return [].concat.apply([], candidateGroups2);
    } else {
        var range = [];
        for (var i = 0, len = optionCounts2[questionIndex]; i < len; i++) {
            range.push(i);
        }
        return permute(range, p);
    }
}

function generateVoteCode(questionIndex, optionIndex) {
    if (voteCodeTypeIsShort) {
        return shortVoteCodes[questionIndex][permutations[questionIndex].indexOf(optionIndex)];
    } else if (voteCodeTypeIsLong) {
        var key = base32.toBits(credential);
        var msg = [serialNumber, tag, questionIndex, 'vote_code', optionIndex].join(',')
        var hmac = new sjcl.misc.hmac(key, sjcl.hash.sha256);
        var digest = base32.fromBits(hmac.encrypt(msg), voteCodeLength);
        return digest.slice(digest.length - voteCodeLength);
    }
}

function validateCheckCharacter(string, chars) {
    // Luhn mod N algorithm.
    // https://en.wikipedia.org/wiki/Luhn_mod_N_algorithm#Algorithm
    var factor = 1;
    var sum = 0;
    var n = chars.length;
    // Starting from the right, work leftwards.
    // Now, the initial "factor" will always be "1".
    // since the last character is the check character.
    for (var i = string.length - 1; i >= 0; i--) {
        var codePoint = chars.indexOf(string.charAt(i));
        var addend = factor * codePoint;
        // Alternate the "factor" that each "codePoint" is multiplied by.
        factor = (factor == 2) ? 1 : 2;
        // Sum the digits of the "addend" as expressed in base "n".
        addend = Math.floor(addend / n) + (addend % n);
        sum += addend;
    }
    var remainder = sum % n;
    return (remainder == 0);
}

function verifyHash(secret, hash) {
    var hashArray = hash.split('$');
    // Select the appropriate PRF.
    var prf;
    switch (hashArray[0]) {
        case 'pbkdf2_sha256':
            prf = sjcl.misc.hmac;
            break;
        case 'pbkdf2_sha512':
            prf = function (key) {
                sjcl.misc.hmac.call(this, key, sjcl.hash.sha512);
            };
            prf.prototype = new sjcl.misc.hmac('');
            prf.prototype.constructor = prf;
            break;
        default:
            throw new Error("Unsupported hash: " + hash);
    }
    // Verify the secret.
    var iterations = parseInt(hashArray[1]);
    var salt = hashArray[2];
    var digest = sjcl.codec.base64.toBits(hashArray[3]);
    return sjcl.bitArray.equal(digest, sjcl.misc.pbkdf2(secret, salt, iterations, null, prf));
}

function shuffleArray(array) {
    // https://stackoverflow.com/a/12646864
    for (var i = array.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var temp = array[i];
        array[i] = array[j];
        array[j] = temp;
    }
}
