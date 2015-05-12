# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import demos_utils.enums
import demos_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('ballot_id', models.PositiveIntegerField()),
                ('credential_hash', models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('option_name', models.CharField(max_length=128)),
                ('option_value', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Election',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('election_id', models.CharField(unique=True, max_length=8)),
                ('text', models.CharField(max_length=128)),
                ('ballots', models.PositiveIntegerField()),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('state', demos_utils.fields.IntEnumField(cls=demos_utils.enums.State)),
            ],
        ),
        migrations.CreateModel(
            name='OptData',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('votecode', models.PositiveSmallIntegerField()),
                ('receipt', models.CharField(max_length=6)),
                ('voted', models.BooleanField(default=False)),
                ('order', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=128)),
                ('order', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('question_id', models.PositiveSmallIntegerField()),
                ('text', models.CharField(max_length=128)),
                ('election', models.ForeignKey(to='demos_vbb.Election')),
            ],
        ),
        migrations.CreateModel(
            name='Side',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
                ('side_id', models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B')])),
                ('permindex_hash', models.CharField(max_length=64)),
                ('permindex', models.CharField(max_length=8, blank=True, default='')),
                ('ballot', models.ForeignKey(to='demos_vbb.Ballot')),
            ],
        ),
        migrations.AddField(
            model_name='option',
            name='question',
            field=models.ForeignKey(to='demos_vbb.Question'),
        ),
        migrations.AddField(
            model_name='optdata',
            name='question',
            field=models.ForeignKey(to='demos_vbb.Question'),
        ),
        migrations.AddField(
            model_name='optdata',
            name='side',
            field=models.ForeignKey(to='demos_vbb.Side'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(to='demos_vbb.Election'),
        ),
        migrations.AlterUniqueTogether(
            name='side',
            unique_together=set([('ballot', 'side_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='question',
            unique_together=set([('election', 'question_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='option',
            unique_together=set([('question', 'text')]),
        ),
        migrations.AlterUniqueTogether(
            name='optdata',
            unique_together=set([('side', 'question', 'votecode')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballot',
            unique_together=set([('election', 'ballot_id')]),
        ),
    ]
