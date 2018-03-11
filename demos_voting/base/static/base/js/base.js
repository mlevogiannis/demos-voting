var languageAndTimezoneForm = $('#language-and-timezone-form');
var languageAndTimezoneModal = $('#language-and-timezone-modal');

languageAndTimezoneForm.find(':input').change(function () {
    languageAndTimezoneForm.data('changed', true);
});

languageAndTimezoneForm.submit(function (e) {
    if (!languageAndTimezoneForm.data('changed')) {
      e.preventDefault();
      languageAndTimezoneModal.modal('hide');
    }
});

languageAndTimezoneModal.on('hidden.bs.modal', function (e) {
    if (languageAndTimezoneForm.data('changed')) {
        languageAndTimezoneForm.trigger('reset').data('changed', false);
    }
})

if (typeof showLanguageAndTimezoneModal !== 'undefined' && showLanguageAndTimezoneModal) {
    languageAndTimezoneModal.modal('show');
}

$('[data-toggle="tooltip"]').tooltip();
