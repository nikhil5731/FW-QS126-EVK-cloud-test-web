import copy
import typing

def is_builtin(var_type: type):
    return var_type in [bool, float, int, str]

def obj_from_dict(top: type, obj_dict: dict):    
    obj_dict_copy = copy.deepcopy(obj_dict) # to prevent issues with references changing things in multiple places
    if top is dict:
        return obj_dict_copy

    result = dict()
    for var_name, var_annot in top.__annotations__.items():
        if is_builtin(var_annot) or typing.get_origin(var_annot) is typing.Literal:
            result[var_name] = obj_dict_copy[var_name]
        elif type(var_annot) is type(object): # class
            result[var_name] = obj_from_dict(var_annot, obj_dict_copy[var_name])
        elif typing.get_origin(var_annot) is list:
            result[var_name] = []
            var_annot = var_annot.__args__[0]
            if is_builtin(var_annot) or typing.get_origin(var_annot) is typing.Literal:
                result[var_name] = obj_dict_copy[var_name]
            else:
                result[var_name] = [obj_from_dict(var_annot, item) for item in obj_dict_copy[var_name]]

    return top(**result)

def dict_from_obj(obj):
    obj_copy = copy.deepcopy(obj) # to prevent issues with references changing things in multiple places
    if type(obj) is dict:
        return obj_copy
    
    result = {}
    for var_name, var in obj_copy.__dict__.items():
        var_type = type(var)
        if is_builtin(var_type):
            result[var_name] = var
            continue # next var
        
        elif var_type is list:
            if not len(var):
                result[var_name] = var
                continue # next var

            var_type = type(var[0])
            if is_builtin(var_type):
                result[var_name] = var
            else:
                result[var_name] = [dict_from_obj(var_i) for var_i in var]

        else:
            result[var_name] = dict_from_obj(var)
    return result