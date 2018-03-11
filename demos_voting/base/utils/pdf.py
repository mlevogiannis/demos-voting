from __future__ import absolute_import, division, print_function, unicode_literals

import io
import math
import os
import re
import subprocess

import PIL

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext as _

from reportlab.graphics.barcode.qr import QrCode
from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib import colors, enums, pagesizes
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

from six.moves import zip, zip_longest


def _load_font(family, style):
    try:
        filename = subprocess.check_output(
            ['fc-list', '-f', '%{file}', ':family=%s:style=%s' % (family, style)],
            universal_newlines=True
        )
    except OSError as e:
        raise EnvironmentError("fc-list: %s" % e)
    if not filename:
        raise EnvironmentError("Missing font for: family='%s', style='%s'" % (family, style))
    name = os.path.splitext(os.path.basename(filename))[0]
    registerFont(TTFont(name, filename))
    return name


def _load_image(filename, width=None, height=None, black_only=False):
    filename = os.path.join(settings.BASE_DIR, filename)
    pil_image = PIL.Image.open(filename)
    if black_only:
        for x in range(pil_image.width):
            for y in range(pil_image.height):
                pixel = pil_image.getpixel((x, y))
                pil_image.putpixel((x, y), (0, 0, 0, pixel[3]))
    image_file = io.BytesIO()
    pil_image.save(image_file, pil_image.format)
    image_file.seek(0)
    if (width is None and height is not None) or (width is not None and height is None):
        aspect_ratio = float(pil_image.height) / float(pil_image.width)
        if width is None:
            width = aspect_ratio * height
        elif height is None:
            height = aspect_ratio * width
    return Image(image_file, width=width, height=height)


class BallotPDF(object):
    PAGE_SIZE = pagesizes.A4

    LEFT_MARGIN = RIGHT_MARGIN = 36
    TOP_MARGIN = BOTTOM_MARGIN = 28

    PAGE_WIDTH = PAGE_SIZE[0] - (LEFT_MARGIN + RIGHT_MARGIN)
    PAGE_HEIGHT = PAGE_SIZE[1] - (TOP_MARGIN + BOTTOM_MARGIN)

    FONT_SMALL = 9
    FONT_MEDIUM = 12
    FONT_LARGE = 14

    FONT_SANS_BOLD = _load_font('Liberation Sans', 'Bold')
    FONT_SANS_ITALIC = _load_font('Liberation Sans', 'Italic')
    FONT_SANS_REGULAR = _load_font('Liberation Sans', 'Regular')
    FONT_MONO_BOLD = _load_font('Liberation Mono', 'Bold')
    FONT_MONO_REGULAR = _load_font('Liberation Mono', 'Regular')

    SPACER_HEIGHT_SMALL = 4
    SPACER_HEIGHT_MEDIUM = 8
    SPACER_HEIGHT_LARGE = 16

    QR_CODE_SIZE = 104

    LOGO_IMAGE = _load_image(
        filename='demos_voting/base/static/base/img/LOGO_FINAL_1.png',
        width=174,
        black_only=True,
    )

    KEY_VALUE_PARAGRAPH_STYLE = ParagraphStyle(
        name='key_value',
        fontSize=FONT_MEDIUM,
        firstLineIndent=-20,
        leftIndent=20,
        leading=16,
    )

    HEADER_TABLE_CELL_HORIZONTAL_PADDING = 6

    HEADER_TABLE_STYLE = TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
        ('ALIGN', (4, 0), (4, 0), 'RIGHT'),
        ('FONT', (0, 0), (0, 0), FONT_SANS_BOLD),
        ('FONT', (1, 0), (1, 0), FONT_MONO_BOLD),
        ('FONT', (3, 0), (3, 0), FONT_SANS_BOLD),
        ('FONT', (4, 0), (4, 0), FONT_MONO_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), FONT_LARGE),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), HEADER_TABLE_CELL_HORIZONTAL_PADDING),
        ('LEFTPADDING', (1, 0), (1, 0), HEADER_TABLE_CELL_HORIZONTAL_PADDING),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('LEFTPADDING', (-2, 0), (-2, 0), 0),
        ('RIGHTPADDING', (-2, 0), (-2, 0), HEADER_TABLE_CELL_HORIZONTAL_PADDING),
        ('LEFTPADDING', (-1, 0), (-1, 0), HEADER_TABLE_CELL_HORIZONTAL_PADDING),
        ('RIGHTPADDING', (-1, 0), (-1, 0), 0),
    ])

    FOOTER_TABLE_STYLE = TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (2, 0), (2, 0), 'TOP'),
        ('FONT', (2, 0), (2, 0), FONT_SANS_BOLD),
        ('FONTSIZE', (2, 0), (2, 0), 130),
        ('TOPPADDING', (2, 0), (2, 0), -30),
    ])

    OPTION_TABLE_CELL_HORIZONTAL_PADDING = 6

    OPTION_TABLE_STYLE = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (2, -1), 2, colors.black),
        ('BOX', (4, 0), (-1, -1), 2, colors.black),
        ('INNERGRID', (0, 0), (2, -1), 0.25, colors.black),
        ('INNERGRID', (4, 0), (-1, -1), 0.25, colors.black),
        ('LINEBELOW', (0, 0), (2, 0), 1, colors.black),
        ('LINEBELOW', (4, 0), (-1, 0), 1, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), OPTION_TABLE_CELL_HORIZONTAL_PADDING),
        ('RIGHTPADDING', (0, 0), (-1, -1), OPTION_TABLE_CELL_HORIZONTAL_PADDING),
    ])

    OPTION_TABLE_LAYOUT_2_COLUMN_SEPARATOR_WIDTH = 12

    OPTION_TABLE_PARAGRAPH_STYLE = ParagraphStyle(
        name='option_table',
        fontSize=FONT_SMALL,
        alignment=enums.TA_CENTER,
    )

    OPTION_TABLE_SANS_BOLD_PARAGRAPH_STYLE = OPTION_TABLE_PARAGRAPH_STYLE.clone(
        name='option_table_sans_bold',
        fontName=FONT_SANS_BOLD,
    )

    OPTION_TABLE_SANS_REGULAR_PARAGRAPH_STYLE = OPTION_TABLE_PARAGRAPH_STYLE.clone(
        name='option_table_sans_regular',
        fontName=FONT_SANS_REGULAR,
    )

    OPTION_TABLE_SANS_ITALIC_PARAGRAPH_STYLE = OPTION_TABLE_PARAGRAPH_STYLE.clone(
        name='option_table_sans_italic',
        fontName=FONT_SANS_ITALIC,
    )

    OPTION_TABLE_MONO_REGULAR_PARAGRAPH_STYLE = OPTION_TABLE_PARAGRAPH_STYLE.clone(
        name='option_table_mono_regular',
        fontName=FONT_MONO_REGULAR,
        splitLongWords=False,
    )

    HELP_PARAGRAPH_STYLE = ParagraphStyle(
        name='help',
        fontName=FONT_SANS_REGULAR,
        fontSize=FONT_MEDIUM,
        alignment=enums.TA_CENTER,
    )

    def __init__(self, election):
        self.election = election

    def generate(self, ballot):
        doc_file = io.BytesIO()
        doc = BaseDocTemplate(
            filename=doc_file,
            pagesize=self.PAGE_SIZE,
            author="DEMOS Voting",
            subject=_("Election %(slug)s") % {'slug': self.election.slug},
            title=_("Ballot %(serial_number)s") % {'serial_number': ballot.serial_number},
        )
        flowables = []
        for i, ballot_part in enumerate(ballot.parts.all()):
            page_template = self._get_page_template(ballot_part)
            doc.addPageTemplates(page_template)
            if i > 0:
                flowables.append(NextPageTemplate(page_template.id))
                flowables.append(PageBreak())
            flowables.extend(self._get_page_body(ballot_part.questions.all()))
        flowables.append(PageBreak())
        doc.build(flowables)
        return doc_file

    def _get_page_template(self, ballot_part):
        header_flowables = self._get_page_header(ballot_part)
        header_height = sum(flowable.wrap(self.PAGE_WIDTH, self.PAGE_HEIGHT)[1] for flowable in header_flowables)
        footer_flowables = self._get_page_footer(ballot_part)
        footer_height = sum(flowable.wrap(self.PAGE_WIDTH, self.PAGE_HEIGHT)[1] for flowable in footer_flowables)

        def _draw_page_header(canvas, doc):
            height = self.PAGE_HEIGHT + self.BOTTOM_MARGIN
            for flowable in header_flowables:
                height -= flowable.wrapOn(canvas, self.PAGE_WIDTH, self.PAGE_HEIGHT)[1]
                flowable.drawOn(canvas, self.LEFT_MARGIN, height)

        def _draw_page_footer(canvas, doc):
            height = self.BOTTOM_MARGIN
            for flowable in reversed(footer_flowables):
                h = flowable.wrapOn(canvas, self.PAGE_WIDTH, self.PAGE_HEIGHT)[1]
                flowable.drawOn(canvas, self.LEFT_MARGIN, height)
                height += h

        frame = Frame(
            id='frame_%s' % ballot_part.tag,
            x1=self.LEFT_MARGIN,
            y1=self.BOTTOM_MARGIN + footer_height,
            width=self.PAGE_WIDTH,
            height=self.PAGE_HEIGHT - (header_height + footer_height),
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
        )
        page_template = PageTemplate(
            id='template_%s' % ballot_part.tag,
            frames=frame,
            pagesize=self.PAGE_SIZE,
            onPage=_draw_page_header,
            onPageEnd=_draw_page_footer,
        )
        return page_template

    def _get_page_header(self, ballot_part):
        election = self.election
        ballot = ballot_part.ballot

        def _key_width(text):
            return stringWidth(text, self.FONT_SANS_BOLD, self.FONT_LARGE) + self.HEADER_TABLE_CELL_HORIZONTAL_PADDING

        def _value_width(text):
            return stringWidth(text, self.FONT_MONO_BOLD, self.FONT_LARGE) + self.HEADER_TABLE_CELL_HORIZONTAL_PADDING

        left_key = _("Serial number:")
        left_value = ballot.serial_number
        left_key_width = _key_width(left_key)
        left_value_width = _value_width(force_text(100 + election.ballot_count - 1))

        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            if election.security_code_length is not None:
                right_key = _("Security code:")
                right_value = ballot_part.get_security_code_display()
            else:
                right_key = ""
                right_value = ""
        elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            right_key = _("Credential:")
            right_value = ballot_part.get_credential_display()
        right_key_width = _key_width(right_key)
        right_value_width = _value_width(right_value)

        flowables = [
            Table(
                data=[(left_key, left_value, "", right_key, right_value)],
                colWidths=[left_key_width, left_value_width, '*', right_key_width, right_value_width],
                style=self.HEADER_TABLE_STYLE,
            ),
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_SMALL + self.SPACER_HEIGHT_MEDIUM),
            Drawing(self.PAGE_WIDTH, 0.5, Line(x1=0, y1=0, x2=self.PAGE_WIDTH, y2=0, strokeWidth=0.5)),
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_LARGE),
        ]
        return flowables

    def _get_page_footer(self, ballot_part):
        election = self.election
        qr_code = QrCode(
            value=ballot_part.voting_booth_url,
            qrLevel='M',
            qrBorder=0,
            width=self.QR_CODE_SIZE,
            height=self.QR_CODE_SIZE,
        )
        flowables = [
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_LARGE),
            Drawing(self.PAGE_WIDTH, 0.5, Line(x1=0, y1=0, x2=self.PAGE_WIDTH, y2=0, strokeWidth=0.5)),
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_MEDIUM),
            self._get_key_value_paragraph(
                key=_("Vote Collector"),
                value=ballot_part.voting_booth_url,
                font=self.FONT_MONO_REGULAR,
            ),
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_MEDIUM),
            self._get_key_value_paragraph(
                key=_("Bulletin board"),
                value=election.bulletin_board_url,
                font=self.FONT_MONO_REGULAR,
            ),
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_MEDIUM),
            Table(
                data=[(qr_code, self.LOGO_IMAGE, ballot_part.tag)],
                colWidths=[self.PAGE_WIDTH / 3] * 3,
                style=self.FOOTER_TABLE_STYLE,
            ),
            Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_MEDIUM),
            Paragraph(
                text=_(
                    "Every ballot consists of two equivalent parts, A and B. Please randomly choose one part to use "
                    "for voting and keep the other part for verification."
                ),
                style=self.HELP_PARAGRAPH_STYLE,
            ),
        ]
        return flowables

    def _get_page_body(self, ballot_questions):
        election = self.election
        election_questions = election.questions.all()
        # Add the election's name.
        flowables = [
            self._get_key_value_paragraph(
                key=_("Election"),
                value=escape(election.name),
                font=self.FONT_SANS_REGULAR,
            ),
        ]
        # Split the options into tables.
        if election.type == election.TYPE_QUESTION_OPTION:
            options_per_table = [
                zip(election_question.options.all(), ballot_question.options.all())
                for election_question, ballot_question
                in zip(election_questions, ballot_questions)
            ]
        elif election.type == election.TYPE_PARTY_CANDIDATE:
            candidate_options = zip(election_questions[1].options.all(), ballot_questions[1].options.all())
            candidate_count_per_party = election_questions[1].option_count // election_questions[0].option_count
            options_per_table = list(zip(*([iter(candidate_options)] * candidate_count_per_party)))
        # Prepare the option tables.
        for i, options in enumerate(options_per_table):
            flowables += [
                Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_LARGE),
            ]
            if election.type == election.TYPE_QUESTION_OPTION:
                # Add the question's name.
                election_question = election_questions[i]
                if election.question_count > 1:
                    question_name_key = _("Question %(index)d") % {'index': election_question.index + 1}
                else:
                    question_name_key = _("Question")
                flowables += [
                    self._get_key_value_paragraph(
                        key=question_name_key,
                        value=escape(election_question.get_name_display()),
                        font=self.FONT_SANS_REGULAR,
                    ),
                ]
            elif election.type == election.TYPE_PARTY_CANDIDATE:
                # Add the party's name, vote-code and receipt.
                election_question = election_questions[1]
                party_election_option = election_questions[0].options.all()[i]
                party_ballot_option = ballot_questions[0].options.all()[i]
                flowables += [
                    KeepTogether([
                        self._get_key_value_paragraph(
                            key=_("Party name"),
                            value=escape(party_election_option.get_name_display()),
                            font=(self.FONT_SANS_REGULAR if party_election_option.name else self.FONT_SANS_ITALIC),
                        ),
                        Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_SMALL),
                        self._get_key_value_paragraph(
                            key=_("Party vote-code"),
                            value=party_ballot_option.get_vote_code_display(),
                            font=self.FONT_MONO_REGULAR,
                        ),
                        Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_SMALL),
                        self._get_key_value_paragraph(
                            key=_("Party receipt"),
                            value=party_ballot_option.get_receipt_display(),
                            font=self.FONT_MONO_REGULAR,
                        ),
                    ]),
                ]
            # Prepare the option table's header row.
            if election.type == election.TYPE_QUESTION_OPTION:
                header_name_text = _("Option")
                header_vote_code_text = _("Vote-code")
                header_receipt_text = _("Receipt")
            elif election.type == election.TYPE_PARTY_CANDIDATE:
                header_name_text = _("Candidate name")
                header_vote_code_text = _("Candidate vote-code")
                header_receipt_text = _("Candidate receipt")
            header_name_paragraph = Paragraph(
                text=header_name_text,
                style=self.OPTION_TABLE_SANS_BOLD_PARAGRAPH_STYLE,
            )
            header_vote_code_paragraph = Paragraph(
                text=header_vote_code_text,
                style=self.OPTION_TABLE_SANS_BOLD_PARAGRAPH_STYLE,
            )
            header_receipt_paragraph = Paragraph(
                text=header_receipt_text,
                style=self.OPTION_TABLE_SANS_BOLD_PARAGRAPH_STYLE,
            )
            header_row = (header_name_paragraph, header_vote_code_paragraph, header_receipt_paragraph)
            # Prepare the option table's body rows.
            body_rows = []
            for election_option, ballot_option in options:
                if election_option.name is not None:
                    body_name_style = self.OPTION_TABLE_SANS_REGULAR_PARAGRAPH_STYLE
                elif election.type == election.TYPE_PARTY_CANDIDATE:
                    body_name_style = self.OPTION_TABLE_SANS_ITALIC_PARAGRAPH_STYLE
                body_name_paragraph = Paragraph(
                    text=escape(election_option.get_name_display()),
                    style=body_name_style,
                )
                body_vote_code_paragraph = Paragraph(
                    text=ballot_option.get_vote_code_display(),
                    style=self.OPTION_TABLE_MONO_REGULAR_PARAGRAPH_STYLE,
                )
                body_receipt_paragraph = Paragraph(
                    text=ballot_option.get_receipt_display(),
                    style=self.OPTION_TABLE_MONO_REGULAR_PARAGRAPH_STYLE,
                )
                body_rows.append((body_name_paragraph, body_vote_code_paragraph, body_receipt_paragraph))
            # Calculate the option table's column widths.
            name_paragraphs, vote_code_paragraphs, receipt_paragraphs = zip(*([header_row] + body_rows))
            vote_code_column_width = max(p.minWidth() for p in vote_code_paragraphs[:2])
            receipt_column_width = max(p.minWidth() for p in receipt_paragraphs[:2])
            if election_question.option_table_layout == election_question.OPTION_TABLE_LAYOUT_1_COLUMN:
                remaining_width = self.PAGE_WIDTH
            elif election_question.option_table_layout == election_question.OPTION_TABLE_LAYOUT_2_COLUMN:
                remaining_width = (self.PAGE_WIDTH - self.OPTION_TABLE_LAYOUT_2_COLUMN_SEPARATOR_WIDTH) / 2
            remaining_width -= vote_code_column_width + receipt_column_width
            for p in name_paragraphs:
                p.wrap(remaining_width - 3 * 2 * self.OPTION_TABLE_CELL_HORIZONTAL_PADDING, self.PAGE_HEIGHT)
            name_column_width = max(max(p.getActualLineWidths0()) for p in name_paragraphs)
            remaining_width -= name_column_width
            if remaining_width > 0:
                name_column_width += remaining_width / 3
                vote_code_column_width += remaining_width / 3
                receipt_column_width += remaining_width / 3
            # Add the option table.
            if election_question.option_table_layout == election_question.OPTION_TABLE_LAYOUT_1_COLUMN:
                rows = [header_row] + body_rows
                column_widths = [
                    name_column_width,
                    vote_code_column_width,
                    receipt_column_width,
                ]
            elif election_question.option_table_layout == election_question.OPTION_TABLE_LAYOUT_2_COLUMN:
                row_index = int(math.ceil(len(body_rows) / 2))
                rows1 = [header_row] + body_rows[:row_index]
                rows2 = [header_row] + body_rows[row_index:]
                rows = [row1 + ("",) + row2 for row1, row2 in zip_longest(rows1, rows2, fillvalue=("", "", ""))]
                column_widths = [
                    name_column_width,
                    vote_code_column_width,
                    receipt_column_width,
                    self.OPTION_TABLE_LAYOUT_2_COLUMN_SEPARATOR_WIDTH,
                    name_column_width,
                    vote_code_column_width,
                    receipt_column_width,
                ]
            flowables += [
                Spacer(width=self.PAGE_WIDTH, height=self.SPACER_HEIGHT_MEDIUM),
                Table(
                    data=rows,
                    colWidths=column_widths,
                    style=self.OPTION_TABLE_STYLE,
                ),
            ]
        return flowables

    def _get_key_value_paragraph(self, key, value, font):
        try:
            URLValidator()(value)
        except ValidationError:
            pass
        else:
            value = "<link href='%(url)s'>%(url)s</link>" % {
                'url': value,
            }
        text = "<font name='%(key_font)s'>%(key)s:&nbsp;</font><font name='%(value_font)s'>%(value)s</font>" % {
            'key': re.sub(r'\s+', '&nbsp;', key),
            'key_font': self.FONT_SANS_BOLD,
            'value': value,
            'value_font': font,
        }
        return Paragraph(text, self.KEY_VALUE_PARAGRAPH_STYLE)
