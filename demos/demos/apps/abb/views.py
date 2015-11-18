# File: views.py

from __future__ import division, unicode_literals

import os
import json
import hmac
import math
import hashlib
import logging

from io import BytesIO
from base64 import b64decode
from datetime import timedelta
from itertools import dropwhile

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

from google.protobuf import message

from django import http
from django.db import models, transaction
from django.apps import apps
from django.core import exceptions
from django.utils import timezone
from django.conf.urls import include, url
from django.db.models import Count, Max, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.core.files import File
from django.middleware import csrf
from django.views.generic import View
from django.db.models.query import QuerySet
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.core.serializers.json import DjangoJSONEncoder

from demos.apps.abb.tasks import tally_protocol
from demos.apps.abb.models import Election, Question, Ballot, Part, OptionV, \
    Task

from demos.common.utils import api, base32cf, dbsetup, enums, intc, hashers
from demos.common.utils.config import registry
from demos.common.utils.permutation import permute_ori

logger = logging.getLogger(__name__)
app_config = apps.get_app_config('abb')
config = registry.get_config('abb')
hasher = hashers.PBKDF2Hasher()


class HomeView(View):
    
    template_name = 'abb/home.html'
    
    def get(self, request):
        return render(request, self.template_name, {})


class AuditView(View):
    
    template_name = 'abb/audit.html'
    
    def get(self, request, *args, **kwargs):
        
        election_id = kwargs.get('election_id')
        
        normalized = base32cf.normalize(election_id)
        if normalized != election_id:
            return redirect('abb:audit', election_id=normalized)
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            election = None
        else:
            questions = Question.objects.filter(election=election)
        
        if not election:
            return redirect(reverse('abb:home') + '?error=id')
        
        participants = Ballot.objects.filter(election=election, \
            part__optionv__voted=True).distinct().count() if election else 0
        
        context = {
            'election': election,
            'questions': questions,
            'participants': str(participants),
            'Vc': { s.name: s.value for s in enums.Vc },
        }
        
        csrf.get_token(request)
        return render(request, self.template_name, context)


class ResultsView(View):
    
    template_name = 'abb/results.html'
    
    def get(self, request, *args, **kwargs):
        
        election_id = kwargs.get('election_id')
        
        normalized = base32cf.normalize(election_id)
        if normalized != election_id:
            return redirect('abb:results', election_id=normalized)
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            election = None
        else:
            questions = Question.objects.filter(election=election)
        
        if not election:
            return redirect(reverse('abb:home') + '?error=id')
        
        participants = Ballot.objects.filter(election=election, \
            part__optionv__voted=True).distinct().count() if election else 0
        
        questions = questions.annotate(Sum('optionc__votes'))
        
        context = {
            'election': election,
            'questions': questions,
            'participants': str(participants),
            'State': { s.name: s.value for s in enums.State },
        }
        
        csrf.get_token(request)
        return render(request, self.template_name, context)


class SetupView(View):
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(SetupView, self).dispatch(*args, **kwargs)
    
    def get(self, request):
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            task = request.POST['task']
            election_obj = json.loads(request.POST['payload'])
            
            if task == 'election':
                
                cert_dump = election_obj['cert'].encode()
                cert_file = File(BytesIO(cert_dump), name='cert.pem')
                election_obj['cert'] = cert_file
                
                dbsetup.election(election_obj, app_config)
                election = Election.objects.get(id=election_obj['id'])
                
                scheduled_time = election.end_datetime + timedelta(seconds=5)
                
                task = tally_protocol.s(election.id)
                task.freeze()
                
                Task.objects.create(election=election, task_id=task.id)
                task.apply_async(eta=scheduled_time)
                
            elif task == 'ballot':
                dbsetup.ballot(election_obj, app_config)
            else:
                raise Exception('SetupView: Invalid POST task: %s' % task)
        except Exception:
            logger.exception('SetupView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class UpdateView(View):
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(UpdateView, self).dispatch(*args, **kwargs)
    
    def get(self, request):
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            data = json.loads(request.POST['data'])
            model = app_config.get_model(data['model'])
            
            fields = data['fields']
            natural_key = data['natural_key']
            
            obj = model.objects.get_by_natural_key(**natural_key)
            
            for name, value in fields.items():
                setattr(obj, name, value)
            
            obj.save(update_fields=list(fields.keys()))
        
        except Exception:
            logger.exception('UpdateView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class VoteView(View):
    
    @method_decorator(api.user_required('vbb'))
    def dispatch(self, *args, **kwargs):
        return super(VoteView, self).dispatch( *args, **kwargs)
    
    def get(self, request):
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            votedata = json.loads(request.POST['votedata'])
            
            e_id = votedata['e_id']
            b_serial = votedata['b_serial']
            b_credential = b64decode(votedata['b_credential'].encode())
            p1_index = votedata['p1_index']
            p1_votecodes = votedata['p1_votecodes']
            p2_security_code = votedata['p2_security_code']
            
            election = Election.objects.get(id=e_id)
            ballot = Ballot.objects.get(election=election, serial=b_serial)
            
            # part1 is always the part that the client has used to vote,
            # part2 is the other part.
            
            order = ('' if p1_index == 'A' else '-') + 'index'
            part1, part2 = Part.objects.filter(ballot=ballot).order_by(order)
            
            question_qs = Question.objects.filter(election=election)
            
            # Verify election state
            
            now = timezone.now()
            
            if not(election.state == enums.State.RUNNING and now >= \
                election.start_datetime and now < election.end_datetime):
                raise Exception('Invalid election state')
            
            # Verify ballot's credential
            
            if not hasher.verify(b_credential, ballot.credential_hash):
                raise Exception('Invalid ballot credential')
            
            # Verify part2's security code
            
            _, salt, iterations = part2.security_code_hash2.split('$')
            hash,_,_=hasher.encode(p2_security_code,salt[::-1],iterations,True)
            
            if not hasher.verify(hash, part2.security_code_hash2):
                raise Exception('Invalid part security code')
            
            # Check if the ballot is already used
            
            part_qs = [part1, part2]
            if OptionV.objects.filter(part__in=part_qs, voted=True).exists():
                raise Exception('Ballot already used')
            
            # Common long votecode values
            
            if election.vc_type == enums.Vc.LONG:
                
                max_options = question_qs.annotate(Count('optionc')).\
                    aggregate(Max('optionc__count'))['optionc__count__max']
                
                credential_int = intc.from_bytes(b_credential, 'big')
                
                key = base32cf.decode(p2_security_code)
                bytes = int(math.ceil(key.bit_length() / 8))
                key = intc.to_bytes(key, bytes, 'big')
            
            # Verify vote's correctness and save it to the db in an atomic
            # transaction. If anything fails, rollback and return the error.
            
            with transaction.atomic():
                for question in question_qs.iterator():
                    
                    optionv_qs = OptionV.objects.\
                        filter(part=part1, question=question)
                    
                    optionv2_qs = OptionV.objects.\
                        filter(part=part2, question=question)
                    
                    vc_name = 'votecode'
                    vc_list = p1_votecodes[str(question.index)]
                    
                    if len(vc_list) < 1:
                        raise Exception('Not enough votecodes')
                    
                    if len(vc_list) > question.choices:
                        raise Exception('Too many votecodes')
                    
                    # Long votecode version: use hashes instead of votecodes
                    
                    if election.vc_type == enums.Vc.LONG:
                        
                        l_votecodes = vc_list
                        
                        vc_list = [hasher.encode(vc, part1.l_votecode_salt, \
                            part1.l_votecode_iterations, True)[0] \
                            for vc in vc_list]
                        
                        vc_name = 'l_' + vc_name + '_hash'
                    
                    # Get options for the requested votecodes
                    
                    vc_filter = {vc_name + '__in': vc_list}
                    
                    optionv_not_qs = optionv_qs.exclude(**vc_filter)
                    optionv_qs = optionv_qs.filter(**vc_filter)
                    
                    # If lengths do not match, at least one votecode was invalid
                    
                    if optionv_qs.count() != len(vc_list):
                        raise Exception('Invalid votecode')
                    
                    # Save both voted and unvoted options
                    
                    if election.vc_type == enums.Vc.SHORT:
                        
                        optionv_qs.update(voted=True)
                        optionv_not_qs.update(voted=False)
                        optionv2_qs.update(voted=False)
                        
                    elif election.vc_type == enums.Vc.LONG:
                        
                        # Save the requested long votecodes
                        
                        for optionv, l_votecode in zip(optionv_qs, l_votecodes):
                            optionv.voted = True
                            optionv.l_votecode = l_votecode
                            optionv.save(update_fields=['voted', 'l_votecode'])
                        
                        optionv_not_qs.update(voted=False)
                        
                        # Compute part2's long votecodes
                        
                        for optionv2 in optionv2_qs:
                            
                            msg = credential_int + (question.index * \
                                max_options) + optionv2.votecode
                            bytes = int(math.ceil(msg.bit_length() / 8))
                            msg = intc.to_bytes(msg, bytes, 'big')
                            
                            hmac_obj = hmac.new(key, msg, hashlib.sha256)
                            digest = intc.from_bytes(hmac_obj.digest(), 'big')
                            
                            l_votecode = base32cf.\
                                encode(digest)[-config.VOTECODE_LEN:]
                            
                            optionv2.voted = False
                            optionv2.l_votecode = l_votecode
                            optionv2.save(update_fields=['voted', 'l_votecode'])
                
                # Save part2's security code
                
                part2.security_code = p2_security_code
                part2.save(update_fields=['security_code'])
        
        except Exception:
            logger.exception('VoteView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class ExportView(View):
    
    template_name = 'abb/export.html'
    
    def __post_election(o, v, d):
        ''' o: objects, v: value, d: default '''
        return d if o['Election'].state != enums.State.COMPLETED else v
    
    _namespaces = {
        'election': {
            'model': Election,
            'args': [('id', '[' + base32cf._valid_re + ']+')],
            'fields': ['cert', 'coins', 'id', 'vc_type'],
            'cache': 'export_file',
            'next': ['ballot', 'question_fk'],
        },
        'ballot': {
            'model': Ballot,
            'args': [('serial', '[0-9]+')],
            'fields': ['serial'],
            'next': ['part'],
        },
        'part': {
            'model': Part,
            'args': [('index', '[AaBb]')],
            'fields': ['index', 'l_votecode_iterations', 'l_votecode_salt',
                'security_code'],
            'callback': lambda o, f, v, d, _func=__post_election:
                v or None if f in ('l_votecode_iterations', 'l_votecode_salt') \
                else _func(o, v, d) or None if f == 'security_code' else v,
            'next': ['question'],
        },
        'question': {
            'model': Question,
            'args': [('index', '[0-9]+')],
            'fields': ['index'],
            'next': ['option'],
        },
        'option': {
            'model': OptionV,
            'name': 'option',
            'args': [('index', '[0-9]+')],
            'fields': ['com', 'index', 'l_votecode', 'l_votecode_hash',
                'receipt_full', 'votecode', 'voted', 'zk1', 'zk2'],
            'callback': lambda o, f, v, d, _func=__post_election:
                v or None if f == 'l_votecode_hash' else \
                _func(o, v, d) if f in ('voted', 'zk2') else \
                _func(o, v, d) or None if f == 'l_votecode' else v,
        },
        'question_fk': {
            'model': Question,
            'args': [('index', '[0-9]+')],
            'fields': ['combined_com', 'combined_decom', 'index', 'key'],
        },
    }
    
    _namespace_root = ['election']
    
    
    # --------------------------------------------------------------------------
    
    def __update_namespaces(namespaces):
        
        # model: required
        # name: optional, defaults to the model's verbose name
        # args: optional, defaults to an empty list
        # fields: optional, defaults to an empty list
        # files: auto-completed, derives from fields
        # namespaces: auto-completed, derives from next
        # cache: optional, defaults to None
        # callback: optional, defaults to None
        # next: optional, defaults to an empty list
        
        for node in namespaces.values():
            
            node.setdefault('name', node['model']._meta.verbose_name)
            
            for key in ['args', 'fields', 'next']:
                node.setdefault(key, [])
            
            for key in ['cache', 'callback']:
                node.setdefault(key, None)
        
        for node in namespaces.values():
            
            node['namespaces'] = \
                [namespaces[next]['name'] + 's' for next in node['next']]
            
            if set(node['fields']) & set(node['namespaces']):
                raise exceptions.ImproperlyConfigured("'fields' " \
                    "and 'namespaces' must be disjoint sets.")
            
            node['files'] = [field for field in list(node['fields']) \
                if isinstance(node['model']._meta.get_field(field), \
                models.FileField) and not node['fields'].remove(field)]
    
    __update_namespaces(_namespaces)
    
    # --------------------------------------------------------------------------
    
    
    @staticmethod
    def _urlpatterns():
        
        def _build_urlpatterns(ns):
            
            node = ExportView._namespaces[ns]
            
            urlpatterns = []
            for next in node['next']:
                urlpatterns += _build_urlpatterns(next)
            
            argpath = '/'.join(['(?P<' + node['model'].__name__ + '__' + \
                field + '>' + regex + ')' for field, regex in node['args']])
            
            urlpatterns = [url(r'^' + node['name'] + 's/', include([
                url(r'^$', ExportView.as_view(), name='schema'),
                url(r'^' + argpath + '/', include([
                    url(r'^$', ExportView.as_view(), name='data'),
                ] + urlpatterns)),
            ], namespace=ns))]
            
            return urlpatterns
        
        urlpatterns = []
        for ns in ExportView._namespace_root:
            urlpatterns += _build_urlpatterns(ns)
        
        return urlpatterns
    
    
    @staticmethod
    def _export(namespaces, url_args, query_args, url_name):
        
        # Get each namespace's model instance, until the requested one is found
        
        objects = {}
        
        for i, ns in enumerate(namespaces, start=1):
            
            node = ExportView._namespaces[ns]
            
            kwflds = {f.name: objects[k] for k in objects for f
                in node['model']._meta.get_fields() if f.is_relation
                and k == f.related_model.__name__}
            
            kwflds.update(url_args.get(node['model'].__name__, {}))
            
            if i < len(namespaces):
                objects[node['model'].__name__] = \
                    get_object_or_404(node['model'], **kwflds)
        
        # Build and return the requested data
        
        if url_name == 'data':
            
            def _build_data(ns, objects, kwflds):
                
                node = ExportView._namespaces[ns]
                
                # 'obj_fields' is the intersection of the namespace's fields
                # and the fields specified in the namespace's url query. If an
                # url query is not specified, all fields are returned. If the
                # url query is an empty list (or does not contain any valid
                # 'fields'), no fields are returned. In addition to 'fields',
                # the url query may contain 'namespaces', but this does not pose
                # a problem since 'fields' and 'namespaces' are disjoint sets.
                
                f1 = set(node['fields'])
                f2 = set(query_args.get(node['name'], node['fields']))
                
                obj_fields = list(f1 & f2)
                
                # Update input query's fields with the model's related fields
                
                kwflds.update({f.name: objects[k] for k in objects for f
                    in node['model']._meta.get_fields() if f.is_relation
                    and k == f.related_model.__name__})
                
                # Get all model instances as a list of dictionaries
                
                try:
                    obj_qs = node['model'].objects.filter(**kwflds)
                    if not obj_qs:
                        raise ObjectDoesNotExist()
                
                except (ValidationError, ObjectDoesNotExist):
                    raise http.Http404('No %s matches the given query.' % \
                        node['model'].__name__)
                
                obj_data_l = list(obj_qs.values(*obj_fields)) \
                    if obj_fields else [dict() for _ in range(obj_qs.count())]
                
                # Check if the namespace has a callback function
                
                callback = node['callback']
                
                if obj_fields and callback:
                    
                    # In addition to objects, pass each field's default value
                    # to the callback, too. This may or may not be taken into
                    # account when determining the callback's return value.
                    
                    default = {f: node['model'].\
                        _meta.get_field(f).get_default() for f in obj_fields}
                    
                    # Call the callback function for every returned field
                    
                    for obj_data in obj_data_l:
                        for f, v in obj_data.items():
                            obj_data[f] = callback(objects, f, v, default[f])
                
                # Traverse the namespace tree and repeat
                
                objects = objects.copy()
                fields = set(query_args.get(node['name'], node['namespaces']))
                
                for next in node['next']:
                    
                    name = ExportView._namespaces[next]['name'] + 's'
                    
                    if name not in fields:
                        continue
                    
                    for obj, obj_data in zip(obj_qs, obj_data_l):
                        objects[node['model'].__name__] = obj
                        obj_data[name] = _build_data(next, objects, {})
                
                return obj_data_l
            
            # Return the requested model's data
            
            data = _build_data(ns, objects, kwflds)[0]
            
        elif url_name == 'schema':
            
            # Get the list of available input arguments
            
            args = [arg for arg, _ in node['args']]
            
            if args:
                flat = (len(args) == 1)
                object_qs = node['model'].objects.filter(**kwflds)
                values = list(object_qs.values_list(*args, flat=flat))
            else:
                values = []
            
            # Return the requested model's data
            
            data = {
                'fields': sorted(node['fields']),
                'files': sorted(node['files']),
                'namespaces': sorted(node['namespaces']),
                'values': values,
            }
        
        return data
    
    
    @staticmethod
    def _export_file(namespace, url_args, fieldname, filename=None):
        
        model = ExportView._namespaces[namespace]['model']
        
        kwflds = url_args.get(model.__name__, {})
        obj = get_object_or_404(model, **kwflds)
        
        filefield = getattr(obj, fieldname)
        
        if not (filefield and filefield.storage.exists(filefield.name)):
            raise http.Http404('File not found: %s' % fieldname)
        
        filename = os.path.basename(filefield.name) if not filename \
            else filename + os.path.splitext(filefield.name)[-1]
        
        try:
            filefield.open('rb')
        except IOError:
            raise http.Http404('Error opening file: %s' % filename)
        
        response = http.FileResponse(filefield.file)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
            
        return response
    
    
    def get(self, request, **kwargs):
        
        url_name = request.resolver_match.url_name
        
        # Accept case insensitive ballot part indices
        
        if 'Part__index' in kwargs:
            kwargs['Part__index'] = kwargs['Part__index'].upper()
        
        # Ignore any namespaces before root
        
        namespaces = list(dropwhile(lambda ns: \
            ns not in self._namespace_root, request.resolver_match.namespaces))
        
        ns = namespaces[-1]
        node = self._namespaces[ns]
        
        # 'url_args' is a dict containing all captured url arguments (dicts),
        # organized by their model's name
        
        url_args = {}
        
        for key, value in kwargs.items():
            model, field = key.split('__', 1)
            url_args.setdefault(model, {}).update({field: value})
        
        # 'query_args' is a dict containing all url query arguments (lists),
        # organized by their namespace's name
        
        query_args = {k: [s for q in v for s in q.split(',') if s]
            for k, v in request.GET.iterlists()}
        
        # 'html' is a built-in name, no namespace is allowed to use it. If true,
        # return a HTML page with the data, if undefined or false return a file.
        
        html_args = query_args.pop('html', ['false'])
        html = html_args[0].lower() if html_args else ''
        
        if len(html_args) != 1 or html not in ('true', 'false'):
            raise http.Http404('Invalid "html" query: true / false')
        
        # 'schema' does not support any query arguments
        
        if url_name == 'schema' and query_args:
            raise http.Http404('Invalid query: no namespace specified')
        
        # Traverse the namespace tree, starting from the requested namespace and
        # ending to all reachable leaf nodes, and build a dictionary whose keys
        # are the names of each namespace and values are lists of all reachable
        # namespace nodes. This structure is used only for validation.
        
        nodes_by_name = {}
        
        def _build_nodes(_ns):
            node = self._namespaces[_ns]
            fields = set(query_args.get(node['name'], node['namespaces']))
            for next in node['next']:
                if self._namespaces[next]['name'] + 's' not in fields:
                    continue
                _build_nodes(next)
            nodes_by_name.setdefault(node['name'], []).append(node)
        
        _build_nodes(ns)
        
        # Special case: if a file field is requested, it must be the only
        # field of the whole query and a member of the requested namespace
        
        ns_args = query_args.get(node['name'], [])
        
        filefield = ns_args[0] if len(query_args) == 1 and \
            len(ns_args) == 1 and ns_args[0] in node['files'] else None
        
        # Validate input query fields
        
        for name, fields in query_args.items():
            
            _nodes = nodes_by_name.get(name)
            
            if not _nodes:
                raise http.Http404('Invalid namespace: %s' % name)
            
            if not fields:
                raise http.Http404('No fields specified: %s' % name)
            
            f1 = set(fields)
            f2 = set([f for n in _nodes for f in n['fields'] + n['namespaces']])
            f3 = set([f for n in _nodes for f in n['files']])
            
            # Raise an error if an input field is invalid or it is a file and
            # the requirement for files is not fulfilled (see comment above).
            # A node's 'fields', 'files' and 'namespaces' are disjoint sets.
           
            if not (f1 <= f2 or (filefield and f1 <= f3)):
                field_diff = f1 - (f2 | f3)
                
                raise http.Http404('Invalid "%s" fields: %s' % (name, \
                    ', '.join(field_diff) if field_diff else 
                    'a file field cannot be combined with any other '
                    'fields or be selected from a nested namespace.'))
        
        # Return the requested file, if any
        
        if url_name == 'data' and filefield:
            return self._export_file(ns, url_args, filefield, filefield)
        
        # If the namespace has a cache FileField return that cached file,
        # ignoring html, ajax and url query arguments
        
        filefield = node['cache']
        
        if url_name == 'data' and filefield:
            return self._export_file(ns, url_args, filefield, node['name'])
        
        # Export the requested data
        
        data = self._export(namespaces, url_args, query_args, url_name)
        
        # Serialize and return the requested data
        
        encoder = self._CustomJSONEncoder
        
        if html == 'true':
            data = json.dumps(data, indent=4, sort_keys=True, cls=encoder)
            response = render(request, self.template_name, {'data': data})
        
        elif request.is_ajax():
            response = http.JsonResponse(data, safe=False, encoder=encoder)
        
        else:
            response = http.HttpResponse()
            response['Content-Disposition'] = 'attachment; filename="%s.json"' \
                % (node['name'] + ('s' if url_name == 'schema' else ''))
            json.dump(data, response, indent=4, sort_keys=True, cls=encoder)
        
        return response
    
    
    class _CustomJSONEncoder(DjangoJSONEncoder):
        """JSONEncoder subclass that supports date/time and protobuf types."""
        
        from demos.common.utils import protobuf
        
        def default(self, o):
            
            if isinstance(o, message.Message):
                return self.protobuf.to_dict(o, ordered=True)
            
            return super(ExportView._CustomJSONEncoder, self).default(o)

