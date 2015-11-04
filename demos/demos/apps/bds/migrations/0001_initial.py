# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demos.common.utils.enums
import demos.common.utils.storage
import demos.common.utils.fields
import demos.apps.bds.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('serial', models.PositiveIntegerField()),
                ('pdf', models.FileField(upload_to=demos.apps.bds.models.get_ballot_file_path, storage=demos.common.utils.storage.PrivateTarFileStorage(tar_file_permissions_mode=384, tar_permissions_mode=384, tar_directory_permissions_mode=448, location='/var/spool/demos-voting/bds/ballots'))),
            ],
            options={
                'ordering': ['election', 'serial'],
            },
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=128, unique=True)),
                ('value', models.CharField(max_length=128)),
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
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('tag', models.CharField(choices=[('A', 'A'), ('B', 'B')], max_length=1)),
                ('vote_token', models.TextField()),
                ('security_code', models.CharField(max_length=8)),
                ('ballot', models.ForeignKey(to='bds.Ballot')),
            ],
            options={
                'ordering': ['ballot', 'tag'],
            },
        ),
        migrations.CreateModel(
            name='RemoteUser',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=128, unique=True)),
                ('password', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Trustee',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('election', models.OneToOneField(serialize=False, to='bds.Election', primary_key=True)),
                ('task_id', models.UUIDField()),
            ],
        ),
        migrations.AddField(
            model_name='trustee',
            name='election',
            field=models.ForeignKey(to='bds.Election'),
        ),
        migrations.AddField(
            model_name='ballot',
            name='election',
            field=models.ForeignKey(to='bds.Election'),
        ),
        migrations.AlterUniqueTogether(
            name='trustee',
            unique_together=set([('election', 'email')]),
        ),
        migrations.AlterUniqueTogether(
            name='part',
            unique_together=set([('ballot', 'tag')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballot',
            unique_together=set([('election', 'serial')]),
        ),
    ]
