# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import demos_utils.enums
import demos_utils.fields
import demos_bds.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('ballot_id', models.PositiveIntegerField()),
                ('pdf', models.FileField(upload_to=demos_bds.models.Ballot.ballot_path)),
            ],
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('option_name', models.CharField(max_length=128)),
                ('option_value', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Election',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('election_id', models.CharField(max_length=8, unique=True)),
                ('text', models.CharField(max_length=128)),
                ('ballots', models.PositiveIntegerField()),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('state', demos_utils.fields.IntEnumField(cls=demos_utils.enums.State)),
            ],
        ),
        migrations.CreateModel(
            name='Side',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('side_id', models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B')])),
                ('permindex', models.CharField(max_length=8)),
                ('voteurl', models.CharField(max_length=26)),
                ('ballot', models.ForeignKey(to='demos_bds.Ballot')),
            ],
        ),
        migrations.CreateModel(
            name='Trustee',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('email', models.EmailField(max_length=254)),
                ('election', models.ForeignKey(to='demos_bds.Election')),
            ],
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(to='demos_bds.Election'),
        ),
        migrations.AlterUniqueTogether(
            name='trustee',
            unique_together=set([('election', 'email')]),
        ),
        migrations.AlterUniqueTogether(
            name='side',
            unique_together=set([('ballot', 'side_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballot',
            unique_together=set([('election', 'ballot_id')]),
        ),
    ]
