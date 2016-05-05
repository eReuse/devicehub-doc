from ereuse_devicehub.resources.schema import UnitCodes
from ereuse_devicehub.utils import Naming
from ereuse_devicehub.validation import ALLOWED_WRITE_ROLES


class Doc:
    """
    Base class that transforms difficult python-eve like API and schema to something easier
    for documenting programs.
    """
    def get_fields(self, schema, **options):
        """
        Returns a list of dictionaries of the style of :func: `get_field`
        """
        fields = []
        for name, sub_settings in schema.items():
            fields.extend(self.get_field(name, sub_settings, **options))
        return fields

    def get_field(self, field_name: str, schema: dict, **options) -> list:
        """
        Returns a list of a) the passed-in field, and b) inner fields represented by passed-in-fieldname.inner-feldname:
        - reference: the typeName of a data_relation
        - type: the type of the field
        - attr: dictionary of attributes. Nonexisting values are set as None, all keys exist.
        """
        result_field = {'type': schema['type'], 'name': field_name}
        if self.special_cases(result_field, schema, **options):
            return [result_field] + result_field.pop('_inner_fields', [])
        if 'data_relation' in schema:
            result_field['reference'] = Naming.type(schema['data_relation']['resource'])
        elif schema['type'] == 'list' and 'schema' in schema:
            subschema = schema['schema']
            if 'data_relation' in subschema:
                result_field['reference'] = Naming.type(subschema['data_relation']['resource'])
            elif subschema['type'] == 'dict':
                self.get_dict(result_field, subschema['schema'], **options)
        elif schema['type'] == 'dict' and 'schema' in schema:
            self.get_dict(result_field, schema['schema'], **options)
        result_field['attr'] = {
            'Unique': schema.get('unique'),
            'Default': schema.get('default'),
            'Allowed': schema.get('allowed'),
            'Required': schema.get('required'),
            'Description': schema.get('description'),
            'Write only': schema.get('writeonly'),
            'Read only': schema.get('readonly'),
            'Modifiable': schema.get('modifiable'),
            'Sink': schema.get('sink', 0),
            'Unit Code': schema.get('unitCode'),
            'Doc': schema.get('doc'),
            'Roles with writing permission': schema.get(ALLOWED_WRITE_ROLES),
            'OR': schema.get('or'),
            'Excludes': schema.get('excludes')
        }
        if 'unitCode' in schema:
            result_field['attr']['Unit Code'] = UnitCodes.humanize(schema['unitCode']) + ' ({})'.format(schema['unitCode'])
        return [result_field] + result_field.pop('_inner_fields', [])

    def get_dict(self, result_parent_field: dict, schema: dict, **options):
        """
        Updates the field by adding information from the 'schema' field in dict
        :param result_parent_field: Dictionary from :func: `get_field` to update
        :param schema: Schema representing the dictionary
        """
        try:
            result_parent_field['type'] += '_of_{}'.format(schema.type_name())
        except:
            fields = self.get_fields(schema, **options)
            for field in fields:
                field['name'] = result_parent_field['name'] + '.' + field['name']
            result_parent_field['_inner_fields'] = fields

    @staticmethod
    def special_cases(result_field, schema, **options):
        schema_name = options.get('schema_name')
        if schema_name == 'Snapshot' or schema_name == 'Register' or schema_name == 'Device':
            if result_field['name'] == 'device':
                if options.get('method') == 'GET':
                    result_field['type'] = 'str'
                    result_field['reference'] = 'Device'
                else:
                    result_field['type'] = 'dict_of_Device'
            elif result_field['name'] == 'components':
                if options.get('method') == 'GET':
                    result_field['type'] = 'list'
                    result_field['reference'] = 'Component'
                else:
                    result_field['type'] = 'list_of_Component'
