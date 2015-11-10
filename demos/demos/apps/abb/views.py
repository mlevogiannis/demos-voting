# File: views.py

from __future__ import division

import json
import hmac
import math
import hashlib
import logging

from io import BytesIO
from base64 import b64decode
from datetime import timedelta

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

from google.protobuf import message

from django import http
from django.db import transaction
from django.apps import apps
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
        
        try:
            normalized = base32cf.normalize(election_id)
        except (AttributeError, TypeError, ValueError):
            election = None
        else:
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
        }
        
        csrf.get_token(request)
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        
        election_id = kwargs.get('election_id')
        
        if election_id is None:
            return http.HttpResponseNotAllowed(['GET'])
        
        try:
            serial = int(request.POST.get('serial'))
        except ValueError:
            return http.HttpResponse(status=422)
        
        try:
            election = Election.objects.get(id=election_id)
            ballot = Ballot.objects.get(election=election, serial=serial)
            part_qs = Part.objects.filter(ballot=ballot);
            question_qs = Question.objects.filter(election=election);
            
            # Get ballot's api export url
            
            url_args = {
                'Election__id': election.id,
                'Ballot__serial': ballot.serial,
            }
            
            url = reverse('abb-api:export:election:ballot:get', kwargs=url_args)
            
            # Common values
            
            vote = None
            args = ['index','votecode','voted'] if not election.long_votecodes \
                else ['index','l_votecode','voted','l_votecode_hash']
            
            # Iterate over parts, questions and options to build the response
            
            parts = []
            
            for p in part_qs:
                
                extra_args = tuple() if not election.long_votecodes \
                    else (p.l_votecode_salt, p.l_votecode_iterations)
                
                questions = []
                
                for q in question_qs:
                    
                    optionv_qs = OptionV.objects.filter(part=p, question=q)
                    options = list(optionv_qs.values_list(*args))
                    
                    if p.security_code:
                        
                        # If a ballot part has a security code, the other ballot
                        # part was used by the client to vote
                        
                        vote = 'A' if p.tag != 'A' else 'B'
                        
                        # Restore options' correct order
                        
                        int_ = base32cf.decode(p.security_code) + q.index
                        bytes_ = int(math.ceil(int_.bit_length() / 8))
                        value = hashlib.sha256(intc.to_bytes(int_,bytes_,'big'))
                        index = intc.from_bytes(value.digest(), 'big')
                        
                        options = permute_ori(options, index)
                    
                    questions.append((q.index, options))
                
                parts.append((p.tag, questions) + extra_args)
            
            # Return response
            
            response = {
                'url': url,
                'vote': vote,
                'parts': parts,
            }
        
        except (ValidationError, ObjectDoesNotExist):
            return http.HttpResponse(status=422)
        
        return http.JsonResponse(response)


class ResultsView(View):
    
    template_name = 'abb/results.html'
    
    def get(self, request, *args, **kwargs):
        
        election_id = kwargs.get('election_id')
        
        try:
            normalized = base32cf.normalize(election_id)
        except (AttributeError, TypeError, ValueError):
            election = None
        else:
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
                
                cert_dump = election_obj['x509_cert'].encode()
                cert_file = File(BytesIO(cert_dump), name='cert.pem')
                election_obj['x509_cert'] = cert_file
                
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
            p1_tag = votedata['p1_tag']
            p1_votecodes = votedata['p1_votecodes']
            p2_security_code = votedata['p2_security_code']
            
            election = Election.objects.get(id=e_id)
            ballot = Ballot.objects.get(election=election, serial=b_serial)
            
            # part1 is always the part that the client used to vote, part2 is
            # the other part.
            
            order = ('' if p1_tag == 'A' else '-') + 'tag'
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
            
            if election.long_votecodes:
                
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
                    
                    vc_type = 'votecode'
                    vc_list = p1_votecodes[str(question.index)]
                    
                    if len(vc_list) < 1:
                        raise Exception('Not enough votecodes')
                    
                    if len(vc_list) > question.choices:
                        raise Exception('Too many votecodes')
                    
                    # Long votecode version: use hashes instead of votecodes
                    
                    if election.long_votecodes:
                        
                        l_votecodes = vc_list
                        
                        vc_list = [hasher.encode(vc, part1.l_votecode_salt, \
                            part1.l_votecode_iterations, True)[0] \
                            for vc in vc_list]
                        
                        vc_type = 'l_' + vc_type + '_hash'
                    
                    # Get options for the requested votecodes
                    
                    vc_filter = {vc_type + '__in': vc_list}
                    optionv_qs = optionv_qs.filter(**vc_filter)
                    
                    # If lengths do not match, at least one votecode was invalid
                    
                    if optionv_qs.count() != len(vc_list):
                        raise Exception('Invalid votecode')
                    
                    # Mark the voted options
                    
                    if not election.long_votecodes:
                        
                        optionv_qs.update(voted=True)
                        
                    else:
                        
                        # Save the given long votecodes
                        
                        for optionv, l_votecode in zip(optionv_qs, l_votecodes):
                            optionv.voted = True
                            optionv.l_votecode = l_votecode
                            optionv.save(update_fields=['voted', 'l_votecode'])
                        
                        # Compute the other ballot part's long votecodes
                        
                        optionv2_qs = OptionV.objects.\
                            filter(part=part2, question=question)
                        
                        for optionv2 in optionv2_qs:
                            
                            msg = credential_int + (question.index * \
                                max_options) + optionv2.votecode
                            bytes = int(math.ceil(msg.bit_length() / 8))
                            msg = intc.to_bytes(msg, bytes, 'big')
                            
                            hmac_obj = hmac.new(key, msg, hashlib.sha256)
                            digest = intc.from_bytes(hmac_obj.digest(), 'big')
                            
                            l_votecode = base32cf.\
                                encode(digest)[-config.VOTECODE_LEN:]
                            
                            optionv2.l_votecode = l_votecode
                            optionv2.save(update_fields=['l_votecode'])
                
                part2.security_code = p2_security_code
                part2.save(update_fields=['security_code'])
        
        except Exception:
            logger.exception('VoteView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class ExportView(View):
    
    template_name = 'abb/export.html'
    
    _namespaces = {
        'election': {
            'name': 'election',
            'model': Election,
            'args': [('id', '[a-zA-Z0-9]+')],
            'fields': [],
            'next': ['ballot', 'question_fk'],
        },
        'ballot': {
            'name': 'ballot',
            'model': Ballot,
            'args': [('serial', '[0-9]+')],
            'fields': [],
            'next': ['part'],
        },
        'part': {
            'name': 'part',
            'model': Part,
            'args': [('tag', '[AaBb]')],
            'fields': [],
            'next': ['question'],
        },
        'question': {
            'name': 'question',
            'model': Question,
            'args': [('index', '[0-9]+')],
            'fields': [],
            'next': ['option'],
        },
        'option': {
            'name': 'option',
            'model': OptionV,
            'args': [('index', '[0-9]+')],
            'fields': ['com', 'zk1', 'zk2'],
            'next': [],
        },
        'question_fk': {
            'name': 'question',
            'model': Question,
            'args': [('index', '[0-9]+')],
            'fields': ['key'],
            'next': [],
        },
    }
    
    _namespace_root = ['election']
    
    
    @staticmethod
    def urlpatterns():
        
        def _build_urlpatterns(ns):
            
            node = ExportView._namespaces[ns]
            
            urlpatterns = []
            for next in node.get('next', []):
                urlpatterns += _build_urlpatterns(next)
            
            argpath = '/'.join(['(?P<' + node['model'].__name__ + '__' + field \
                + '>' + regex + ')' for field, regex in node.get('args', [])])
            
            urlpatterns = [url(r'^' + node['name'] + 's/', include([
                url(r'^$', ExportView.as_view(), name='list'),
                url(r'^' + argpath + '/', include([
                    url(r'^$', ExportView.as_view(), name='get'),
                ] + urlpatterns)),
            ], namespace=ns))]
            
            return urlpatterns
        
        urlpatterns = []
        for ns in ExportView._namespace_root:
            urlpatterns += _build_urlpatterns(ns['name'])
        
        return urlpatterns
    
    
    @staticmethod
    def objdata(namespaces, url_args, query_args, action):
        
        # Get each namespace's model instance up to the requested one, excluding
        
        objects = {}
        
        for i, ns in enumerate(namespaces, start=1):
            
            node = ExportView._namespaces[ns]
            
            kwflds = {f.name: objects[k] for k in objects for f
                in node['model']._meta.get_fields() if f.is_relation
                and k == f.related_model.__name__}
            
            kwflds.update(url_args.get(node['model'].__name__) or {})
            
            if i < len(namespaces):
                objects[node['model'].__name__] = \
                    get_object_or_404(node['model'], **kwflds)
        
        # Build and return the requested data
        
        if action == 'get':
            
            def _build_data(ns, objects, kwflds):
                
                node = ExportView._namespaces[ns]
                
                # 'fields' is the intersection of the model's fields and the
                # fields specified in the url query, for the current namespace.
                # If no fields are specified, all model's fields are returned.
                # If the url query's value is empty, no fields are returned.
                
                f1 = set(node.get('fields', []))
                f2 = set(query_args.get(node['name'], []))
                
                if not (f2 <= f1):
                    raise http.Http404('Invalid field(s): ' + ', '.join(f2-f1))
                
                fields = list(f1 & f2 if f2 else f1 \
                    if node['name'] not in query_args else set())
                
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
                    raise http.Http404('No "' + node['name'] + \
                        '" matches the given query.')
                
                obj_data_l = list(obj_qs.values(*fields)) \
                    if fields else [dict() for _ in range(obj_qs.count())]
                
                # Traverse the namespace tree and repeat
                
                objects = objects.copy()
                
                for next in node.get('next', []):
                    for obj, obj_data in zip(obj_qs, obj_data_l):
                        
                        objects[node['model'].__name__] = obj
                        name, data = _build_data(next, objects, {})
                        obj_data[name] = data
                
                return (node['name'] + 's', obj_data_l)
            
            # Return the requested model's data
            
            data = _build_data(ns, objects, kwflds)[1][0]
            
        elif action == 'list':
            
            # Return the list of available input arguments and output fields
            
            fields = [field for field, _ in node.get('args', [])]
            
            if fields:
                flat = (len(fields) == 1)
                object_qs = node['model'].objects.filter(**kwflds)
                values = list(object_qs.values_list(*fields, flat=flat))
            else:
                values = []
            
            data = {
                'arguments': values,
                'fields': node.get('fields', []),
            }
        
        return data
        
    
    def get(self, request, **kwargs):
        
        action = request.resolver_match.url_name
        
        # Accept case insensitive ballot part tags
        
        if 'Part__tag' in kwargs:
            kwargs['Part__tag'] = kwargs['Part__tag'].upper()
        
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
        
        # Ignore any namespaces before root
        
        namespaces = list(request.resolver_match.namespaces)
        
        for ns in list(namespaces):
            
            if ns in self._namespace_root:
                break
            
            namespaces.pop(0)
        
        name = self._namespaces[namespaces[-1]]['name']
        
        # Build, serialize and return the requested data
        
        data = self.objdata(namespaces, url_args, query_args, action)
        
        encoder = self.CustomJSONEncoder
        
        if 'file' in request.GET:
            response = http.HttpResponse()
            response['Content-Disposition'] = 'attachment; filename="' + \
                name + ('s' if action == 'list' else '') + '.json"'
            json.dump(data, response, indent=4, sort_keys=True, cls=encoder)
        
        elif request.is_ajax():
            response = http.JsonResponse(data, safe=False, encoder=encoder)
        
        else:
            data = json.dumps(data, indent=4, sort_keys=True, cls=encoder)
            response = render(request, self.template_name, {'data': data})
        
        return response
    
    
    class CustomJSONEncoder(DjangoJSONEncoder):
        """JSONEncoder subclass that supports date/time and protobuf types."""
        
        from demos.common.utils import protobuf
        
        def default(self, o):
            
            if isinstance(o, message.Message):
                return self.protobuf.to_dict(o, ordered=True)
            
            return super(JSONEncoder, self).default(o)

