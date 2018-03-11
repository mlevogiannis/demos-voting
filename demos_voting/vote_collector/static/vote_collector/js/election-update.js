var votingEndDateTimeInput = $('#id_voting_ends_at');

if (votingEndDateTimeInput.length != 0) {
    var dateFormat = votingEndDateTimeInput.data('dateFormat')
        .replace('%Y', 'YYYY')
        .replace('%y', 'YY')
        .replace('%m', 'MM')
        .replace('%d', 'DD')
        .replace('%H', 'HH')
        .replace('%M', 'mm')
        .replace('%S', 'ss');

    votingEndDateTimeInput.data('dateFormat', dateFormat);
    votingEndDateTimeInput.parent('.date').datetimepicker({
        allowInputToggle: true,
        icons: {
            time: 'fa fa-clock-o',
            date: 'fa fa-calendar',
            up: 'fa fa-chevron-up',
            down: 'fa fa-chevron-down',
            previous: 'fa fa-chevron-left',
            next: 'fa fa-chevron-right'
        },
        minDate: moment(votingEndDateTimeInput.val(), dateFormat),
        useCurrent: false,
    });
}
