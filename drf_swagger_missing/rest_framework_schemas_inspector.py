from collections import OrderedDict

import coreschema
from rest_framework import schemas


super_get_link = schemas.AutoSchema.get_link
super_get_serializer_fields = schemas.AutoSchema.get_serializer_fields
super_get_get_filter_fields = schemas.AutoSchema.get_filter_fields


class BetterAutoSchema(schemas.AutoSchema):
    def get_link(self, path, method, base_url):
        link = super_get_link(self, path, method, base_url)
        # link = super().get_link(path, method, base_url)
        method = method.lower()
        method_name = getattr(self.view, 'action', method.lower())
        link._responses = OrderedDict()
        # Add obvious responses based on common action names used in viewsets
        try:
            serializer_name = self.view.get_serializer().__class__.__name__
            if method_name in ('retrieve', 'update', 'partial_update'):
                response = coreschema.Response(status=200, schema=coreschema.Ref('%s_read' % serializer_name))
            elif method_name == 'list':
                response = coreschema.Response(status=200, schema=coreschema.Array(
                    items=coreschema.Ref('%s_read' % serializer_name)))
            elif method_name == 'create':
                response = coreschema.Response(status=201, schema=coreschema.Ref('%s_write' % serializer_name))
            elif method_name == 'destroy':
                response = coreschema.Response(status=204)
            else:
                response = None
            if response:
                link._responses[response.status] = response
        except (AttributeError, AssertionError):
            # not all views have get_serializer
            pass
        # User may want to add responses or overwrite existing
        try:
            # User defined responses come in a list
            for r in self.view.Meta.responses[method_name]:
                link._responses[r.status] = r
        except (AttributeError, KeyError):
            # The view doesn't have Meta, Meta doesn't have .responses or responses doesn't have this method
            pass

        # User may define what content types the view may produce:
        try:
            # User defined responses come in a list
            link._produces = self.view.Meta.produces[method_name]
        except (AttributeError, KeyError):
            # The view doesn't have Meta or Meta doesn't have .produces
            link._produces = []
        return link

    def get_serializer_fields(self, path, method):
        try:
            return super_get_serializer_fields(self, path, method)
        except AssertionError:  # Default behaviour of GenericAPIView is to raise AssertionError
            import logging
            logging.getLogger('drf-swagger-missing').warning('View {} does not have a serializer_class defined, '
                                                             'unable to determine the fields for {} {}'
                                                             ''.format(self.view.__class__.__name__, method, path))
            return []

    def get_filter_fields(self, path, method):
        """Hack to add extra fields"""
        fields = super_get_get_filter_fields(self, path, method)
        method_name = getattr(self.view, 'action', method.lower())
        try:
            fields += self.view.Meta.fields.get(method_name, [])
        except AttributeError:
            # The view doesn't have Meta, Meta doesn't have .fields
            pass
        return fields


schemas.AutoSchema.get_link = BetterAutoSchema.get_link
schemas.AutoSchema.get_serializer_fields = BetterAutoSchema.get_serializer_fields
schemas.AutoSchema.get_filter_fields = BetterAutoSchema.get_filter_fields
