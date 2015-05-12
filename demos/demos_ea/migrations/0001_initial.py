# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import demos_utils.fields
import demos_utils.enums


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('ballot_id', models.PositiveIntegerField()),
                ('credential_hash', models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('option_name', models.CharField(max_length=128)),
                ('option_value', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Election',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
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
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('votecode', models.PositiveSmallIntegerField()),
                ('receipt', models.CharField(max_length=6)),
                ('com', demos_utils.fields.JsonField(dump_kwargs={'separators': (',', ':'), 'indent': None}, load_kwargs={})),
                ('decom', demos_utils.fields.JsonField(dump_kwargs={'separators': (',', ':'), 'indent': None}, load_kwargs={})),
                ('zk1', demos_utils.fields.JsonField(dump_kwargs={'separators': (',', ':'), 'indent': None}, load_kwargs={})),
                ('zk_state', demos_utils.fields.JsonField(dump_kwargs={'separators': (',', ':'), 'indent': None}, load_kwargs={})),
                ('order', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('text', models.CharField(max_length=128)),
                ('order', models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('question_id', models.PositiveSmallIntegerField()),
                ('text', models.CharField(max_length=128)),
                ('key', demos_utils.fields.JsonField(dump_kwargs={'separators': (',', ':'), 'indent': None}, load_kwargs={})),
                ('election', models.ForeignKey(to='demos_ea.Election')),
            ],
        ),
        migrations.CreateModel(
            name='Side',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('side_id', models.CharField(choices=[('A', 'A'), ('B', 'B')], max_length=1)),
                ('permindex_hash', models.CharField(max_length=64)),
                ('ballot', models.ForeignKey(to='demos_ea.Ballot')),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('task_id', models.UUIDField()),
                ('election_id', models.CharField(unique=True, max_length=8)),
            ],
        ),
        migrations.CreateModel(
            name='Trustee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('election', models.ForeignKey(to='demos_ea.Election')),
            ],
        ),
        migrations.AddField(
            model_name='option',
            name='question',
            field=models.ForeignKey(to='demos_ea.Question'),
        ),
        migrations.AddField(
            model_name='optdata',
            name='question',
            field=models.ForeignKey(to='demos_ea.Question'),
        ),
        migrations.AddField(
            model_name='optdata',
            name='side',
            field=models.ForeignKey(to='demos_ea.Side'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(to='demos_ea.Election'),
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
