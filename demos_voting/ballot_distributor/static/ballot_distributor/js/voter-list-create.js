var voterEmailsInput = $('#id_emails');

if (voterEmailsInput.length) {
    voterEmailsInput.data('placeholder', voterEmailsInput.attr('placeholder'));
    voterEmailsInput.removeAttr('placeholder');

    voterEmailsInput.tagsinput({
        maxTags: parseInt(voterEmailsInput.data('maxTags')),
        maxChars: parseInt(voterEmailsInput.data('maxChars')),
        tagClass: 'label label-primary',
        trimValue: true
    });

    voterEmailsInput.tagsinput('input').attr('id', voterEmailsInput.attr('id') + '-tagsinput');
    $('label[for="' + voterEmailsInput.attr('id') + '"]').attr('for', voterEmailsInput.attr('id') + '-tagsinput');

    voterEmailsInput.siblings('.bootstrap-tagsinput').toggleClass('empty', !voterEmailsInput.tagsinput('items').length).prepend($('<span>', {class: 'placeholder'}).text(voterEmailsInput.data('placeholder')));

    voterEmailsInput.on('itemAdded itemRemoved', function(e) {
        var tagsinput = voterEmailsInput.siblings('.bootstrap-tagsinput');
        tagsinput.toggleClass('empty', !tagsinput.children('.tag').length);
    });
}
