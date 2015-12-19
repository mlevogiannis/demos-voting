# File utils.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django import template
from django.template.base import token_kwargs, TemplateSyntaxError

register = template.Library()


@register.assignment_tag(name='tuple')
def tuple_(*args):
    return tuple(args)

# ------------------------------------------------------------------------------

class SetCxtAttrNode(template.Node):
    
    def __init__(self, extra_context):
        self.extra_context = extra_context

    def render(self, context):
        values = {key: val.resolve(context) for key, val
                  in self.extra_context.items()}
        context.update(values)
        return ''

@register.tag(name='assign')
def set_cxt_attr(parser, token):
    
    contents = token.split_contents()
    
    tag_name = contents[0]
    tokens = contents[1:]
    
    extra_context = token_kwargs(tokens, parser)
    
    if not extra_context:
        raise TemplateSyntaxError("%r expected at least one variable "
                                  "assignment" % tag_name)
    
    if tokens:
        raise TemplateSyntaxError("%r received an invalid token: %r" %
                                  (tag_name, tokens[0]))
    
    return SetCxtAttrNode(extra_context)

