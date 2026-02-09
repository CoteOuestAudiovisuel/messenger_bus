class MappingException(Exception):
    pass

def Mapping(entity_class):
    if not entity_class or type(entity_class) == type:
        def decorator(i):
            i._entity_class = entity_class
            return i
        return decorator
    else:
        raise MappingException("entity_class n'est pas correct")