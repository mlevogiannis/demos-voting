from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.utils.pdf import BallotPDF
from demos_voting.election_authority.models import Ballot, BallotOption, BallotPart, BallotQuestion


def generate_sample_ballot_pdf(election_form):
    election = election_form.save(commit=False)
    election.generate_private_key()
    ballot = Ballot(election=election)
    ballot.serial_number = 99  # an invalid serial number
    ballot._parts = []
    for tag in (BallotPart.TAG_A, BallotPart.TAG_B):
        ballot_part = BallotPart(ballot=ballot, tag=tag)
        ballot_part.generate_credential()
        ballot_part.generate_security_code()
        ballot_part._questions = []
        for election_question in election.questions.all():
            ballot_question = BallotQuestion(part=ballot_part, election_question=election_question)
            ballot_question._options = []
            for election_option in election_question.options.all():
                ballot_option = BallotOption(question=ballot_question, index=election_option.index)
                ballot_option.generate_vote_code()
                ballot_option.generate_receipt()
                ballot_question._options.append(ballot_option)
            ballot_part._questions.append(ballot_question)
        ballot._parts.append(ballot_part)
    return BallotPDF(election).generate(ballot)
