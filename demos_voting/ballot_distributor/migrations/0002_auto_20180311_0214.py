# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-03-11 00:14
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ballot_distributor', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='voter',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='electionquestion',
            name='election',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='ballot_distributor.Election'),
        ),
        migrations.AddField(
            model_name='electionoption',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='ballot_distributor.ElectionQuestion'),
        ),
        migrations.AddField(
            model_name='ballotquestion',
            name='election_question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ballot_questions', to='ballot_distributor.ElectionQuestion'),
        ),
        migrations.AddField(
            model_name='ballotquestion',
            name='part',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='ballot_distributor.BallotPart'),
        ),
        migrations.AddField(
            model_name='ballotpart',
            name='ballot',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parts', to='ballot_distributor.Ballot'),
        ),
        migrations.AddField(
            model_name='ballotoption',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='ballot_distributor.BallotQuestion'),
        ),
        migrations.AddField(
            model_name='ballotarchive',
            name='administrator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ballot_archives', to='ballot_distributor.Administrator'),
        ),
        migrations.AddField(
            model_name='ballotarchive',
            name='election',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ballot_archives', to='ballot_distributor.Election'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='archive',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ballots', to='ballot_distributor.BallotArchive'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ballots', to='ballot_distributor.Election'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='voter',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ballot', to='ballot_distributor.Voter'),
        ),
        migrations.AddField(
            model_name='administrator',
            name='election',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='administrators', to='ballot_distributor.Election'),
        ),
        migrations.AddField(
            model_name='administrator',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='voter',
            unique_together=set([('election', 'user', 'email')]),
        ),
        migrations.AlterUniqueTogether(
            name='electionquestion',
            unique_together=set([('election', 'index')]),
        ),
        migrations.AlterUniqueTogether(
            name='electionoption',
            unique_together=set([('question', 'index')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballotquestion',
            unique_together=set([('part', 'election_question')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballotpart',
            unique_together=set([('ballot', 'tag')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballotoption',
            unique_together=set([('question', 'index')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballot',
            unique_together=set([('election', 'serial_number')]),
        ),
        migrations.AlterUniqueTogether(
            name='administrator',
            unique_together=set([('election', 'user', 'email')]),
        ),
    ]