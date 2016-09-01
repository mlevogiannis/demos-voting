# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demos_voting.apps.bds.models
import demos_voting.common.utils.fields
import demos_voting.common.utils.storage
import demos_voting.common.utils.enums


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Ballot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('serial', models.PositiveIntegerField()),
                ('pdf', models.FileField(storage=demos_voting.common.utils.storage.PrivateTarFileStorage(tar_directory_permissions_mode=448, tar_file_permissions_mode=384, tar_permissions_mode=384, location='/home/marios/demos/devel/data/bds/ballots'), upload_to=demos_voting.apps.bds.models.get_ballot_file_path)),
            ],
            options={
                'ordering': ['election', 'serial'],
            },
        ),
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
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
                ('id', demos_voting.common.utils.fields.Base32Field(serialize=False, primary_key=True)),
                ('title', models.CharField(max_length=128)),
                ('start_datetime', models.DateTimeField()),
                ('end_datetime', models.DateTimeField()),
                ('state', demos_voting.common.utils.fields.IntEnumField(cls=demos_voting.common.utils.enums.State, choices=[(1, b'draft'), (2, b'pending'), (3, b'working'), (4, b'running'), (5, b'completed'), (6, b'paused'), (7, b'error'), (8, b'template')])),
                ('type', demos_voting.common.utils.fields.IntEnumField(cls=demos_voting.common.utils.enums.Type, choices=[(1, b'elections'), (2, b'referendum')])),
                ('vc_type', demos_voting.common.utils.fields.IntEnumField(cls=demos_voting.common.utils.enums.VcType, choices=[(1, b'short'), (2, b'long')])),
                ('ballots', models.PositiveIntegerField()),
            ],
            options={
                'ordering': ['id'],
            },
        ),
        migrations.CreateModel(
            name='Part',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('index', models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B')])),
                ('vote_token', models.TextField()),
                ('security_code', models.CharField(max_length=8)),
                ('ballot', models.ForeignKey(to='bds.Ballot')),
            ],
            options={
                'ordering': ['ballot', 'index'],
            },
        ),
        migrations.CreateModel(
            name='RemoteUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(unique=True, max_length=128)),
                ('password', models.CharField(max_length=128)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Trustee',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('election', models.OneToOneField(primary_key=True, serialize=False, to='bds.Election')),
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
            unique_together=set([('ballot', 'index')]),
        ),
        migrations.AlterUniqueTogether(
            name='ballot',
            unique_together=set([('election', 'serial')]),
        ),
    ]
