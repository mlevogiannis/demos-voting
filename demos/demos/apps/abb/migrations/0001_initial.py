# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demos.common.utils.crypto.crypto_pb2
import demos.common.utils.enums
import demos.apps.abb.models
import demos.common.utils.storage
import demos.common.utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
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
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('key', models.CharField(unique=True, max_length=128)),
                ('value', models.CharField(max_length=128)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Election',
            fields=[
                ('id', demos.common.utils.fields.Base32Field(serialize=False, primary_key=True)),
                ('title', models.CharField(max_length=128)),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('long_votecodes', models.BooleanField()),
                ('state', demos.common.utils.fields.IntEnumField(cls=demos.common.utils.enums.State)),
                ('ballots', models.PositiveIntegerField()),
                ('cert', models.FileField(storage=demos.common.utils.storage.PrivateFileSystemStorage(file_permissions_mode=384, directory_permissions_mode=448, location='/var/spool/demos-voting/abb'), upload_to=demos.apps.abb.models.get_cert_file_path)),
                ('export_file', models.FileField(storage=demos.common.utils.storage.PrivateFileSystemStorage(file_permissions_mode=384, directory_permissions_mode=448, location='/var/spool/demos-voting/abb'), blank=True, upload_to=demos.apps.abb.models.get_export_file_path)),
                ('coins', models.CharField(default='', blank=True, max_length=128)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='OptionC',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('text', models.CharField(max_length=128)),
                ('index', models.PositiveSmallIntegerField()),
                ('votes', models.PositiveIntegerField(default=None, blank=True, null=True)),
            ],
            options={
                'ordering': ['question', 'index'],
            },
        ),
        migrations.CreateModel(
            name='OptionV',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('votecode', models.PositiveSmallIntegerField()),
                ('l_votecode', models.CharField(default='', blank=True, max_length=16)),
                ('l_votecode_hash', models.CharField(default='', blank=True, max_length=128)),
                ('com', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.Com)),
                ('zk1', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.ZK1)),
                ('zk2', demos.common.utils.fields.ProtoField(default=None, blank=True, null=True, cls=demos.common.utils.crypto.crypto_pb2.ZK2)),
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
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('index', models.CharField(choices=[('A', 'A'), ('B', 'B')], max_length=1)),
                ('security_code', models.CharField(default='', blank=True, max_length=8)),
                ('security_code_hash2', models.CharField(max_length=128)),
                ('l_votecode_salt', models.CharField(default='', blank=True, max_length=128)),
                ('l_votecode_iterations', models.PositiveIntegerField(default=None, blank=True, null=True)),
                ('ballot', models.ForeignKey(to='abb.Ballot')),
            ],
            options={
                'ordering': ['ballot', 'index'],
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('text', models.CharField(max_length=128)),
                ('choices', models.PositiveSmallIntegerField()),
                ('key', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.Key)),
                ('index', models.PositiveSmallIntegerField()),
                ('com_sum', demos.common.utils.fields.ProtoField(default=None, blank=True, null=True, cls=demos.common.utils.crypto.crypto_pb2.Com)),
                ('decom_sum', demos.common.utils.fields.ProtoField(default=None, blank=True, null=True, cls=demos.common.utils.crypto.crypto_pb2.Decom)),
            ],
            options={
                'ordering': ['election', 'index'],
            },
        ),
        migrations.CreateModel(
            name='RemoteUser',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('username', models.CharField(unique=True, max_length=128)),
                ('password', models.CharField(max_length=128)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('election', models.OneToOneField(serialize=False, primary_key=True, to='abb.Election')),
                ('task_id', models.UUIDField()),
            ],
        ),
        migrations.AddField(
            model_name='question',
            name='election',
            field=models.ForeignKey(to='abb.Election'),
        ),
        migrations.AddField(
            model_name='question',
            name='m2m_parts',
            field=models.ManyToManyField(to='abb.Part'),
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
            unique_together=set([('ballot', 'index')]),
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
