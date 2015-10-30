# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demos.common.utils.fields
import demos.common.utils.enums
import demos.apps.abb.models
import demos.common.utils.crypto.crypto_pb2


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('serial', models.PositiveIntegerField()),
                ('credential_hash', models.CharField(max_length=128)),
            ],
            options={
                'ordering': ['election', 'serial'],
            },
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=128, unique=True)),
                ('value', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Election',
            fields=[
                ('id', demos.common.utils.fields.Base32Field(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=128)),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('long_votecodes', models.BooleanField()),
                ('state', demos.common.utils.fields.IntEnumField(cls=demos.common.utils.enums.State)),
                ('ballots', models.PositiveIntegerField()),
                ('x509_cert', models.FileField(upload_to=demos.apps.abb.models.Election.get_upload_file_path)),
                ('coins', models.CharField(default='', max_length=128, blank=True)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='OptionC',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('text', models.CharField(max_length=128)),
                ('index', models.PositiveSmallIntegerField()),
                ('votes', models.PositiveIntegerField(default=None, null=True, blank=True)),
            ],
            options={
                'ordering': ['question', 'index'],
            },
        ),
        migrations.CreateModel(
            name='OptionV',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('votecode', models.PositiveSmallIntegerField()),
                ('l_votecode', models.CharField(default='', max_length=16, blank=True)),
                ('l_votecode_hash', models.CharField(default='', max_length=128, blank=True)),
                ('com', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.Com)),
                ('zk1', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.ZK1)),
                ('zk2', demos.common.utils.fields.ProtoField(default=None, cls=demos.common.utils.crypto.crypto_pb2.ZK2, null=True, blank=True)),
                ('receipt_full', models.TextField()),
                ('voted', models.BooleanField(default=False)),
                ('index', models.PositiveSmallIntegerField()),
            ],
            options={
                'ordering': ['part', 'question', 'index'],
            },
        ),
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('tag', models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B')])),
                ('security_code', models.CharField(default='', max_length=8, blank=True)),
                ('security_code_hash2', models.CharField(max_length=128)),
                ('l_votecode_salt', models.CharField(default='', max_length=128, blank=True)),
                ('l_votecode_iterations', models.PositiveIntegerField(default=None, null=True, blank=True)),
                ('ballot', models.ForeignKey(to='abb.Ballot')),
            ],
            options={
                'ordering': ['ballot', 'tag'],
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('text', models.CharField(max_length=128)),
                ('choices', models.PositiveSmallIntegerField()),
                ('key', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.Key)),
                ('index', models.PositiveSmallIntegerField()),
                ('com', demos.common.utils.fields.ProtoField(default=None, cls=demos.common.utils.crypto.crypto_pb2.Com, null=True, blank=True)),
                ('decom', demos.common.utils.fields.ProtoField(default=None, cls=demos.common.utils.crypto.crypto_pb2.Decom, null=True, blank=True)),
                ('verified', models.BooleanField(default=False)),
                ('election', models.ForeignKey(to='abb.Election')),
                ('m2m_parts', models.ManyToManyField(to='abb.Part')),
            ],
            options={
                'ordering': ['election', 'index'],
            },
        ),
        migrations.CreateModel(
            name='RemoteUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=128, unique=True)),
                ('password', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('task_id', models.UUIDField()),
                ('election_id', demos.common.utils.fields.Base32Field(unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='optionv',
            name='part',
            field=models.ForeignKey(to='abb.Part'),
        ),
        migrations.AddField(
            model_name='optionv',
            name='question',
            field=models.ForeignKey(to='abb.Question'),
        ),
        migrations.AddField(
            model_name='optionc',
            name='question',
            field=models.ForeignKey(to='abb.Question'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(to='abb.Election'),
        ),
        migrations.AlterUniqueTogether(
            name='question',
            unique_together=set([('election', 'index')]),
        ),
        migrations.AlterUniqueTogether(
            name='part',
            unique_together=set([('ballot', 'tag')]),
        ),
        migrations.AlterUniqueTogether(
            name='optionv',
            unique_together=set([('part', 'question', 'index')]),
        ),
        migrations.AlterUniqueTogether(
            name='optionc',
            unique_together=set([('question', 'text')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballot',
            unique_together=set([('election', 'serial')]),
        ),
    ]
