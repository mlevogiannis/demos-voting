// Slug field.

function slugify(value) {
    return value.toString()
        .replace(/[^\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\w\s-]+/g, '')
        .replace(/^[-\s]+/, '')
        .replace(/[-\s]+$/, '')
        .replace(/[-\s]+/g, '-')
        .toLowerCase();
}

$('#id_election-name').on('input', function (e) {
    var slugField = $('#id_election-slug');
    if (!slugField.data('changed')) {
        var name = $(this).val();
        var maxLength = parseInt(slugField.attr('maxlength'));
        var slug = slugify(name).substring(0, maxLength);
        slugField.val(slug);
        slugField.trigger('input');
    }
});

$('#id_election-slug').change(function (e) {
    $(this).data('changed', $(this).val().length > 0);
});

// Election type.

$('input:radio[name="election-type"]').change(function () {
    var typeValue = $(this).filter(':checked').val();
    var questionOption = $('#question-table').closest('.form-group');
    var partyCandidate = $('#party-table, #id_election-max_candidate_selection_count, #id_election-candidate_option_table_layout_0').closest('.form-group');
    if (typeValue == 'question_option') {
        questionOption.removeClass('hidden');
        partyCandidate.addClass('hidden');
    } else if (typeValue == 'party_candidate') {
        questionOption.addClass('hidden');
        partyCandidate.removeClass('hidden');
    } else {
        questionOption.addClass('hidden');
        partyCandidate.addClass('hidden');
    }
});

// Date/time pickers.

$('#id_election-voting_starts_at, #id_election-voting_ends_at').each(function (index, element) {
    $(this).data('dateFormat',
        $(this).data('dateFormat')
            .replace('%Y', 'YYYY')
            .replace('%y', 'YY')
            .replace('%m', 'MM')
            .replace('%d', 'DD')
            .replace('%H', 'HH')
            .replace('%M', 'mm')
            .replace('%M', 'ss')
    );
});

$('#id_election-voting_starts_at, #id_election-voting_ends_at').parent('.date').datetimepicker({
    allowInputToggle: true,
    icons: {
        time: 'fa fa-clock-o',
        date: 'fa fa-calendar',
        up: 'fa fa-chevron-up',
        down: 'fa fa-chevron-down',
        previous: 'fa fa-chevron-left',
        next: 'fa fa-chevron-right'
    },
    minDate: moment().startOf('day'),
    useCurrent: false,
});

// Hide the security code input if the vote-code type is long.

$('input[type=radio][name="election-vote_code_type"]').change(function() {
    var enableSecurityCodeCheckbox = $('#id_election-enable_security_code');
    var disable = ($(this).val() == 'long');
    enableSecurityCodeCheckbox.prop('disabled', disable);
    enableSecurityCodeCheckbox.closest('.form-group').toggleClass('hidden', disable);
});

// Trustee emails.

var trusteeEmailsInput = $('#id_election-trustee_emails');
trusteeEmailsInput.data('placeholder', trusteeEmailsInput.attr('placeholder'));
trusteeEmailsInput.removeAttr('placeholder');

trusteeEmailsInput.tagsinput({
    maxTags: parseInt(trusteeEmailsInput.data('maxTags')),
    maxChars: parseInt(trusteeEmailsInput.data('maxChars')),
    tagClass: 'label label-primary',
    trimValue: true
});

trusteeEmailsInput.tagsinput('input').attr('id', trusteeEmailsInput.attr('id') + '-tagsinput');
$('label[for="' + trusteeEmailsInput.attr('id') + '"]').attr('for', trusteeEmailsInput.attr('id') + '-tagsinput');

trusteeEmailsInput.siblings('.bootstrap-tagsinput').toggleClass('empty', !trusteeEmailsInput.tagsinput('items').length).prepend($('<span>', {class: 'placeholder'}).text(trusteeEmailsInput.data('placeholder')));

trusteeEmailsInput.on('itemAdded itemRemoved', function(e) {
    var tagsinput = trusteeEmailsInput.siblings('.bootstrap-tagsinput');
    tagsinput.toggleClass('empty', !tagsinput.children('.tag').length);
});

// Formset management.

function updateFormset(formset) {
    var forms = formset.children('.formset-form:not(.formset-form-empty, .formset-form-removed)');
    var removedForms = formset.children('.formset-form.formset-form-removed');
    forms.each(function(index) {
        updateForm($(this), index);
    });
    removedForms.each(function(index) {
        updateForm($(this), forms.length + index);
    });
}

function updateForm(form, formIndex) {
    var formset = form.parent('.formset');
    var formsetPrefix = formset.attr('data-formset-prefix');
    var formPrefix = formsetPrefix + '-' + formIndex;
    var formPrefixRegex = new RegExp(formsetPrefix + '-(?:__prefix__|\\d+)');
    form.find('*').addBack().each(function(index, element) {
        $.each(this.attributes, function(index, attr) {
            $(element).attr(attr.nodeName, function(index, attrValue) {
                return attrValue.replace(formPrefixRegex, formPrefix);
            });
        });
    });
    form.find('input[name="' + formPrefix + '-ORDER"]').val(formIndex);
    form.find('.formset-form-index:first').text(formIndex + 1);
}

function manageTotalForms(formset, value) {
    var formsetPrefix = formset.attr('data-formset-prefix');
    var totalForms = $('#id_' + formsetPrefix + '-TOTAL_FORMS');
    var maxNumForms = $('#id_' + formsetPrefix + '-MAX_NUM_FORMS');
    totalForms.val(parseInt(totalForms.val()) + value);
    var addButton = $('.formset-add[data-formset-prefix="' + formsetPrefix + '"]');
    var removedForms = formset.children('.formset-form.formset-form-removed');
    addButton.prop('disabled', parseInt(totalForms.val()) - removedForms.length >= parseInt(maxNumForms.val()));
}

$('.formset-add').click(function (e) {
    var formsetPrefix = $(this).attr('data-formset-prefix');
    var formset = $('.formset[data-formset-prefix="' + formsetPrefix + '"]');
    var emptyForm = formset.children('.formset-form-empty');
    var emptyFormCheckedInputs = emptyForm.find('input:checkbox:checked, input:radio:checked');
    var form = emptyForm.clone(true).removeClass('formset-form-empty');
    var formIndex = formset.children('.formset-form:not(.formset-form-empty)').length;
    formset.append(form);
    updateForm(form, formIndex);
    emptyFormCheckedInputs.each(function (index) {
        $(this).prop('checked', true);
    });
    switch (formset.attr('data-formset-type')) {
        case 'modal':
            $('#formset-modal').data('form', form).data('formAdd', true).modal('show');
            break;
        case 'inline':
            manageTotalForms(formset, +1);
            form.removeClass('hidden');
            formset.trigger('formsetFormAdded', [form]);
            break;
    }
});

$('.formset-form-remove').click(function (e) {
    var form = $(this).closest('.formset-form');
    var formPrefix = form.attr('data-formset-form-prefix');
    var formset = form.parent('.formset');
    if ($('#id_' + formPrefix + '-id').val()) {
        $('#id_' + formPrefix + '-DELETE').prop('checked', true);
        form.addClass('formset-form-removed hidden');
    } else {
        form.remove();
        manageTotalForms(formset, -1);
    }
    updateFormset(formset);
    formset.trigger('formsetFormRemoved');
});

$('.formset-form-edit').click(function (e) {
    var form = $(this).closest('.formset-form');
    $('#formset-modal').data('form', form).modal('show');
});

$('.formset-form-save').click(function (e) {
    var modal = $(this).closest('.modal');
    var form = modal.data('form');
    var name = $('#id_' + form.attr('data-formset-form-prefix') + '-name').val();
    form.find('.formset-form-name:first').text(name);
    modal.data('formSave', true);
    modal.modal('hide');
});

$('#formset-modal').on('show.bs.modal', function (e) {
    var modal = $(this);
    var modalBody = modal.find('.modal-body > .row > [class^="col-"]');
    var modalTitle = modal.find('.modal-title');
    var form =  modal.data('form');
    var formset = form.parent('.formset');
    var formFields = form.find('.formset-form-fields:first >').detach();
    modal.data('formFields', formFields);
    modalBody.append(formFields.clone(true));
    modalTitle.text(formset.attr('data-formset-modal-title'));
    formset.trigger('formsetModalShow', [modalBody]);
});

$('#formset-modal').on('shown.bs.modal', function (e) {
    var modal = $(this);
    var modalBody = modal.find('.modal-body > .row > [class^="col-"]');
    var form =  modal.data('form');
    var formset = form.parent('.formset');
    formset.trigger('formsetModalShown', [modalBody]);
});

$('#formset-modal').on('hide.bs.modal', function (e) {
    var modal = $(this);
    var modalBody = modal.find('.modal-body > .row > [class^="col-"]');
    var form = modal.data('form');
    var formset = form.parent('.formset');
    if (modal.data('formSave')) {
        var formset = form.parent('.formset');
        if (modal.data('formAdd')) {
            manageTotalForms(formset, +1);
            form.removeClass('hidden');
        }
    } else {
        if (modal.data('formAdd')) {
            form.remove();
        }
    }
    formset.trigger('formsetModalHide', [modalBody]);
});

$('#formset-modal').on('hidden.bs.modal', function (e) {
    var modal = $(this);
    var modalBody = modal.find('.modal-body > .row > [class^="col-"]');
    var form = modal.data('form');
    var formset = form.parent('.formset');
    var formFields = form.find('.formset-form-fields:first');
    if (modal.data('formSave')) {
        formFields.append(modalBody.children().detach());
        if (modal.data('formAdd')) {
            formset.trigger('formsetFormAdded', [form]);
        } else {
            formset.trigger('formsetFormEdited', [form]);
        }
    } else {
        modalBody.empty();
        if (!modal.data('formAdd')) {
            formFields.append(modal.data('formFields'));
        }
    }
    modal.find('.modal-title').text('');
    modal.removeData();
});

// Update min_selection_count/max_selection_count input min and max values.

function updateOptionMinMaxSelectionCount(optionFormset) {
    var optionFormsetPrefix = optionFormset.attr('data-formset-prefix');
    var questionFormsetPrefix = optionFormsetPrefix.replace(/-option$/, '');
    var totalForms = parseInt($('#id_' + optionFormsetPrefix + '-TOTAL_FORMS').val());
    var removedForms = optionFormset.children('.formset-form.formset-form-removed').length;
    var minSelectionCount = $('#id_' + questionFormsetPrefix + '-min_selection_count');
    var maxSelectionCount = $('#id_' + questionFormsetPrefix + '-max_selection_count');
    var minSelectionCountValue = parseInt(minSelectionCount.val());
    var maxSelectionCountValue = parseInt(maxSelectionCount.val());
    minSelectionCount.attr('min', 0);
    minSelectionCount.attr('max', Math.max(0, !isNaN(maxSelectionCountValue) && maxSelectionCountValue > 0 && maxSelectionCountValue < totalForms - removedForms - 1 ? maxSelectionCountValue : totalForms - removedForms - 1));
    maxSelectionCount.attr('min', Math.max(1, !isNaN(minSelectionCountValue) && minSelectionCountValue > 1 && minSelectionCountValue < totalForms - removedForms ? minSelectionCountValue : 1));
    maxSelectionCount.attr('max', Math.max(1, totalForms - removedForms));
}

$('.option-formset').on('formsetFormAdded formsetFormRemoved', function (e) {
    updateOptionMinMaxSelectionCount($(this));
});

$('#id_question-__prefix__-min_selection_count, #id_question-__prefix__-max_selection_count').change(function (e) {
    updateOptionMinMaxSelectionCount($(this).closest('.modal-body').find('.option-formset'));
});

$('.party-formset').on('formsetFormAdded formsetFormEdited formsetFormRemoved', function (e) {
    var partyFormset = $(this);
    var partyFormsetPrefix = partyFormset.attr('data-formset-prefix');
    var partyForms = partyFormset.children('.formset-form:not(.formset-form-empty, .formset-form-removed)');
    var maxSelectionCount = 1;
    partyForms.each(function (index) {
        var partyForm = $(this);
        var candidateFormsetPrefix = partyForm.attr('data-formset-form-prefix') + '-candidate';
        var candidateFormset = $('.formset[data-formset-prefix="' + candidateFormsetPrefix + '"]');
        var totalForms = parseInt($('#id_' + candidateFormsetPrefix + '-TOTAL_FORMS').val());
        var removedForms = candidateFormset.children('.formset-form.formset-form-removed').length;
        maxSelectionCount = Math.max(maxSelectionCount, totalForms - removedForms);
    });
    $('#id_election-max_candidate_selection_count').attr('max', maxSelectionCount);
});

// Set focus to the new input.

$('.question-formset, .party-formset').on('formsetModalShown', function (e, modalBody) {
    modalBody.find('input[type!="hidden"]:first').focus();
});

$('.option-formset, .candidate-formset').on('formsetFormAdded', function (e, form) {
    $('#id_' + form.attr('data-formset-form-prefix') + '-name').focus();
});

// Remove error class on input change.

$('input').on('input change', function (e) {
    $(this).closest('.form-group').removeClass('has-error');
});

$('.date').on('dp.change', function (e) {
    $(this).closest('.form-group').removeClass('has-error');
});

// Scroll to the new form.

$('.question-formset, .party-formset').on('formsetFormAdded', function (e, form) {
    $('body').animate({
        scrollTop: $('body').scrollTop() + form.height()
    }, 'fast');
});

$('.option-formset, .candidate-formset').on('formsetFormAdded', function (e, form) {
    var modal = $('#formset-modal');
    modal.scrollTop(modal.scrollTop() + form.height());
});

// Sortable formset table.

function registerSortableFormsetTable(formset) {
    formset.sortable({
        onStart: function (e) {
            $(e.from).parent('table').removeClass('table-hover');
        },
        onEnd: function (e) {
            $(e.to).parent('table').addClass('table-hover');
        },
        onUpdate: function (e) {
            var formset = $(e.item).parent('tbody.formset');
            updateFormset(formset);
            formset.trigger('formsetFormReordered');
        }
    });
}

registerSortableFormsetTable($('.question-formset'));

$('.question-formset').on('formsetModalShow', function (e, modalBody) {
    registerSortableFormsetTable(modalBody.find('.option-formset'));
});

$('.question-formset').on('formsetModalHide', function (e, modalBody) {
    modalBody.find('.option-formset').sortable('destroy');
});

// Ballot preview modal.

$('#pdf-download').attr('href', $('#pdf-object').attr('data'));

$(':input').on('change update remove', function(e) {
    $(this).closest('form').data('changed', true);
});

$('.date').on('dp.change dp.update', function(e) {
    $(this).closest('form').data('changed', true);
});

$('.formset').on('formsetFormAdded formsetFormEdited formsetFormRemoved formsetFormReordered', function(e) {
    $(this).closest('form').data('changed', true);
});

$('button[name="ballot-preview"]').click(function(e) {
    if ($('#pdf-modal').length > 0 && !$('#election-form').data('changed')) {
        e.preventDefault();
        $('#pdf-modal').modal('show');
    }
});

$('#pdf-modal').modal('show');
