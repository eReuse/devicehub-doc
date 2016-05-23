from os.path import expanduser

from devicehub_doc.doc import Doc


class ApiToRST(Doc):
    """
    Generates a RST file compatible with `sphinxcontrib.httpdomain`.
    """

    def __init__(self, app):
        self.doc = 'API\n===\n'
        self.config = app.config
        self.filename = 'api.rst'
        resource_settings = app.config['DOMAIN']
        for key in sorted(resource_settings):
            self.doc += self.document_resource(resource_settings[key])
        self.write()

    def write(self):
        with open(expanduser('~') + '/' + self.filename, '+w') as out:
            out.write(self.doc)
        print("API doc written.")

    def document_resource(self, settings: dict):
        one_successful = False
        type_name = settings['_schema'].type_name()
        doc = '{}\n--------------------\n'.format(type_name)
        for method in settings['resource_methods']:
            try:
                doc += self.document_endpoint(settings, method, True)
            except EmptyError:
                pass
            else:
                one_successful = True
        for method in settings['item_methods']:
            try:
                doc += self.document_endpoint(settings, method, False)
            except EmptyError:
                pass
            else:
                one_successful = True
        if type_name == 'Account':
            settings['url'] = 'login'
            doc += self.document_endpoint(settings, 'POST', True)
        if not one_successful:
            return ''
        else:
            return doc

    def document_endpoint(self, settings: dict, method: str, resource):
        item_url = '/({}:_id)'.format(settings.get('item_url', 'string')) if not resource else ''
        database = '(string:database)/' if method != 'login' else ''
        space = '   '
        doc = [
            '.. http:{}:: {}\n\n'.format(method.lower(), database + settings['url'] + item_url),
            '',
        ]
        if 'additional_lookup' in settings and not resource:
            lookup = settings['additional_lookup']
            doc.append(
                space + ' {}: {}/*({}:{})*'.format('Additional Lookup', database + settings['url'], lookup['url'],
                                                   lookup['field']))
            doc.append('')

        doc.extend([
            space + ':reqheader Accept: "application/json"',
            space + ':resheader Content-Type: "application/json"',
            space + ':resheader Date: The server date',
            space + ':resheader Content-Length:',
            space + ':resheader Server:',
            space + ':statuscode 400:',
            space + ':statuscode 422: Document fails validation.',
            space + ':statuscode 403:',
            space + ':statuscode 404:',
            space + ':statuscode 405:',
            space + ':statuscode 406:',
            space + ':statuscode 415:',
            space + ':statuscode 500: Any non-documented error. Please, report if you get this code.'
        ])
        if settings.get('url') != 'login':
            doc.extend([
                space + ':reqheader Authorization: "Basic" + space + token from *POST /login*',
            ])
            if method == 'POST':
                doc.append(space + ':statuscode 201:')
            elif method == 'DELETE':
                doc.append(space + ':statuscode 204:')
            else:
                doc.append(space + ':statuscode 200:')
            if not resource:
                doc.extend([
                    space + ':resheader Cache-Control: max-age={}, must-revalidate'.format(self.config['ITEM_CACHE']),
                    space + ':resheader Last-Modified: The date when the resource was modified',
                    space + ':resheader Link: The link at the context, as in http://www.w3.org/ns/json-ld#context',
                ])
            else:
                doc.extend([
                    space + ':resheader Cache-Control: max-age=1, must-revalidate'
                ])
            doc.append(self.get_resource_schema(settings, settings['_schema'](False), method, resource))
        else:
            doc.extend([
                space + ':<json string email: The email of the account.',
                space + ':<json string password: The password of the account.',
                space + ':>json string token: The token of the user to use in `Authorization` header.',
                space + ':>json string password: The password of the user.',
                space + ':>json string role:',
                space + ':>json string email:',
                space + ':>json string _id:',
                space + ':>json list databases:',
                space + ':>json string defaultDatabase:'
            ])
        # doc += '\n' + tabulate(self.fields(settings['_schema'](), method), headers='keys', tablefmt='rst')
        return '\n'.join(doc) + '\n\n'

    def get_resource_schema(self, settings, schema, method, resource):
        """
        Gets all the fields from the Schema, interesting for the point of view of the resource
        :param settings:
        :param schema:
        :param method:
        :param resource:
        :raises EmptyError: When there are no regular fields in the Schema
        :return:
        """
        fields = []
        schema_name = settings['_schema'].type_name()
        space = '   '
        json_type = 'jsonarr' if resource and method == 'GET' else 'json'
        if method != 'DELETE' and method != 'PATCH':
            chevron = '<' if method == 'POST' else '>'
            fields.extend(
                self.get_formatted_fields(schema, method=method, space=space, chevron=chevron, schema_name=schema_name,
                                          settings=settings, json_type=json_type))
            # Special fields
            prefix = space + ':>{} {} {}:'
            if '_id' not in schema:
                fields.append((prefix.format(json_type, 'string', self.config['ID_FIELD']), 10))
            fields.append((prefix.format(json_type, 'datetime', self.config['LAST_UPDATED']), -10))
            fields.append((prefix.format(json_type, 'datetime', self.config['DATE_CREATED']), -10))

        # Special fields for GET resource
        prefix = space + ':>json {} {}: {}'
        if method == 'GET' and resource:
            fields.extend([
                (prefix.format('list', '_items', 'Contains the actual data, *Response JSON Array of Objects*.'), -10),
                (prefix.format('dict', '_meta', 'Provides pagination data.'), -10),
                (prefix.format('natural', '_meta.max_results', 'Maximum number of elements in `_items`.'), -10),
                (prefix.format('natural', '_meta.total', 'Total of elements.'), -10),
                (prefix.format('natural', '_meta.page', 'Actual page number.'), -10),
                (prefix.format('dict', '_links',
                               'Provides `HATEOAS` directives. In concrete a link to *itself* and to the *parent*. See http://python-eve.org/features.html#hateoas.'),
                 -10),
            ])
        elif method != 'DELETE':
            fields.append((prefix.format('dict', '_links',
                                         'Provides `HATEOAS` directives. In concrete a link to *itself*, the *parent* endpoint and the *collection* endpoint. See http://python-eve.org/features.html#hateoas.'),
                           -10))

        # Extra response fields
        if (method == 'POST' or method == 'PATCH') and 'extra_response_fields' in settings:
            for field_name in settings['extra_response_fields']:
                try:
                    fields.extend(self.get_formatted_field(field_name, schema[field_name], space=space, chevron='>',
                                                       schema_name=schema_name, settings=settings, method=method,
                                                       json_type=json_type))
                except EmptyError:
                    pass
        # Sorting and final preparation
        fields.sort(key=Doc.get_sink, reverse=True)
        fields.append(space + ':<json object {}: See "Meta" for more information.'.format(self.config['META']))
        return '\n'.join([elem[0] for elem in fields])

    def get_formatted_fields(self, schema: dict, **options) -> list:
        """
        Gets all the formatted fields
        :raises EmptyError: If no fields
        :return: list of (formatted_field, sink)
        """
        fields = []
        for field_name, inner_schema in schema.items():
            try:
                fields.extend(self.get_formatted_field(field_name, inner_schema, **options))
            except EmptyError:
                pass
        if len(fields) == 0:
            raise EmptyError()
        return fields

    def get_formatted_field(self, field_name, schema, **options) -> list:
        prefix = options['space'] + ':{}{} '.format(options['chevron'], options['json_type'])
        fields = self.get_field(field_name, schema, **options)
        formatted_fields = []
        for field in fields:
            required = '\*' if field['attr'].pop('Required') else ''
            field_type = '{}->{}'.format(field['type'], field['reference']) if 'reference' in field else field['type']
            sink = field['attr'].pop('Sink')
            attr = ['{}: {}'.format(name, value) for name, value in field['attr'].items() if value is not None]
            formatted_field = prefix + '{} {}{}: '.format(field_type, required, field['name']) + ', '.join(attr)
            formatted_fields.append((formatted_field, sink))
        return formatted_fields

    def get_field(self, field_name, schema, **options) -> list:
        method = options.get('method')
        if not (schema.get('readonly', False) and (method == 'POST' or method == 'PATCH' or method == 'PUT')) \
                and not (schema.get('writeonly', False) and method == 'GET') \
                and not (not schema.get('modifiable', True) and (method == 'PATCH' or method == 'PUT')):
            # Removing fields that are not projected
            if method == 'GET':
                try:
                    if not options['settings']['datasource']['projection'][field_name]:
                        raise EmptyError()
                except KeyError:
                    pass
            return super().get_field(field_name, schema, **options)
        else:
            raise EmptyError()


class EmptyError(Exception):
    pass
