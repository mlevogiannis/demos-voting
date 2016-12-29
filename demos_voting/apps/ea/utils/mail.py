# File: mail.py

from __future__ import absolute_import, division, print_function, unicode_literals

import textwrap

from django.core import mail
from django.utils.translation import ugettext as _


def make_trustee_message(trustee, index):

    subject = _("DEMOS Voting: Trustee keys for Election %(election_id)s") % {'election_id': trustee.election.id}

    body_main = _(textwrap.dedent(
        """
        Dear %(trustee_email)s,

        Here are your trustee keys for Election %(election_id)s.

        %(trustee_keys)s

        DEMOS Voting: Election Authority
        """
    ))

    body_question = _(textwrap.dedent(
        """
        Question: %(question_index)d
        Key: %(trustee_key)s
        """
    ))

    body = "\n".join(body_main.splitlines()[1:]) % {
        'trustee_email': trustee.email,
        'election_id': trustee.election.id,
        'trustee_keys': "\n".join("".join(
            body_question % {'question_index': question.index, 'trustee_key': question.trustee_keys[index]}
            for question
            in trustee.election.questions.all()
        ).splitlines()[1:]),
    }

    return mail.EmailMessage(subject=subject, body=body, to=[trustee.email])

