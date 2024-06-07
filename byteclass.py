from typing import Literal, TypeVar
import numpy as np

class ByteClass:
    '''
    Expects that all members of the child class have a method equivalent to tobytes() from numpy types.

    Currently only supports integer types.
    '''
    def __post_init__(self):
        for var_name, var_type in self.__annotations__.items():
            self.__dict__[var_name] = var_type(self.__dict__[var_name])

    def to_bytes(self, byteorder: Literal['little', 'big']) -> bytearray:
        result = bytearray()
        if byteorder == 'big':
            raise NotImplementedError('big byteorder not yet supported')
        for var in self.__dict__.values():
            result += var.tobytes(order='C') # TODO is this always going to be little endian or will that change on system?
        return result
    
    def nbytes(self) -> int:
        result = 0
        for var in self.__dict__.values():
            result += var.nbytes
        return result

def nbytes(byte_class: type[ByteClass] | ByteClass):
    result = 0
    for var_type in byte_class.__annotations__.values():
        result += np.dtype(var_type).itemsize
    return result

T = TypeVar('T')
def from_bytes(byte_class: type[T], data: bytearray) -> T:
    if nbytes(byte_class) != len(data):
        raise ValueError()
    init_args = {}
    data_i = 0
    for var_name, var_type in byte_class.__annotations__.items():
        var_size = np.dtype(var_type).itemsize
        init_args[var_name] = np.frombuffer(data[data_i:data_i+var_size], dtype=var_type)[0]
        data_i += var_size
    return byte_class(**init_args)

if __name__ == '__main__':
    from dataclasses import dataclass
    @dataclass
    class ExampleClass(ByteClass):
        var1: np.uint8
        var2: np.int16
        var3: np.uint32
    
    ex_obj = ExampleClass(var1=4, var2=-128, var3=512)
    ex_obj_bytes = ex_obj.to_bytes(byteorder='little')
    print(ex_obj)
    print(ex_obj.nbytes())
    print(nbytes(ExampleClass))
    print(len(ex_obj_bytes))
    print(ex_obj_bytes)

    ex_obj2 = from_bytes(ExampleClass, ex_obj_bytes)
    print(ex_obj2)
