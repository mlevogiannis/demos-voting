# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demos.common.utils.crypto.crypto_pb2
import demos.common.utils.enums
import demos.apps.ea.models
import demos.common.utils.fields
import demos.common.utils.storage


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('serial', models.PositiveIntegerField()),
            ],
            options={
                'ordering': ['election', 'serial'],
            },
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('key', models.CharField(unique=True, max_length=128)),
                ('value', models.CharField(blank=True, max_length=128)),
            ],
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
                ('pkey_file', models.FileField(upload_to=demos.apps.ea.models.get_pkey_file_path, storage=demos.common.utils.storage.PrivateFileSystemStorage(location='/var/spool/demos-voting/ea/pkeys', file_permissions_mode=384, directory_permissions_mode=448))),
                ('pkey_passphrase', models.CharField(max_length=32)),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='OptionC',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('text', models.CharField(max_length=128)),
                ('index', models.PositiveSmallIntegerField()),
            ],
            options={
                'ordering': ['question', 'index'],
            },
        ),
        migrations.CreateModel(
            name='OptionV',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('decom', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.Decom)),
                ('zk_state', demos.common.utils.fields.ProtoField(cls=demos.common.utils.crypto.crypto_pb2.ZKState)),
                ('index', models.PositiveSmallIntegerField()),
            ],
            options={
                'ordering': ['part', 'question', 'index'],
            },
        ),
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('tag', models.CharField(choices=[('A', 'A'), ('B', 'B')], max_length=1)),
                ('ballot', models.ForeignKey(to='ea.Ballot')),
            ],
            options={
                'ordering': ['ballot', 'tag'],
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('text', models.CharField(max_length=128)),
                ('index', models.PositiveSmallIntegerField()),
            ],
            options={
                'ordering': ['election', 'index'],
            },
        ),
        migrations.CreateModel(
            name='RemoteUser',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('username', models.CharField(unique=True, max_length=128)),
                ('password', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Trustee',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('election', models.OneToOneField(serialize=False, to='ea.Election', primary_key=True)),
                ('task_id', models.UUIDField()),
            ],
        ),
        migrations.AddField(
            model_name='trustee',
            name='election',
            field=models.ForeignKey(to='ea.Election'),
        ),
        migrations.AddField(
            model_name='question',
            name='election',
            field=models.ForeignKey(to='ea.Election'),
        ),
        migrations.AddField(
            model_name='question',
            name='m2m_parts',
            field=models.ManyToManyField(to='ea.Part'),
        ),
        migrations.AddField(
            model_name='optionv',
            name='part',
            field=models.ForeignKey(to='ea.Part'),
        ),
        migrations.AddField(
            model_name='optionv',
            name='question',
            field=models.ForeignKey(to='ea.Question'),
        ),
        migrations.AddField(
            model_name='optionc',
            name='question',
            field=models.ForeignKey(to='ea.Question'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(to='ea.Election'),
        ),
        migrations.AlterUniqueTogether(
            name='trustee',
            unique_together=set([('election', 'email')]),
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
