'''
Jupyter Kernel for Kuroko
'''
from ipykernel.kernelbase import Kernel

from pygments.lexers import PythonLexer



import ctypes
from enum import IntEnum

class KrkValueType(IntEnum):
    VAL_NONE      = 0
    VAL_BOOLEAN   = 1
    VAL_INTEGER   = 2
    VAL_FLOATING  = 3
    VAL_HANDLER   = 4
    VAL_OBJECT    = 5
    VAL_KWARGS    = 6

class ObjType(IntEnum):
    OBJ_FUNCTION = 0
    OBJ_NATIVE = 1
    OBJ_CLOSURE = 2
    OBJ_STRING = 3
    OBJ_UPVALUE = 4
    OBJ_CLASS = 5
    OBJ_INSTANCE = 6
    OBJ_BOUND_METHOD = 7
    OBJ_TUPLE = 8
    OBJ_BYTES = 9

class KrkJumpTarget(ctypes.Structure):
    _fields_ = [
        ('type', ctypes.c_ushort),
        ('target', ctypes.c_ushort),
    ]

class KrkObj(ctypes.Structure):
    _fields_ = [
        ('type_', ctypes.c_int),
        ('isMarked', ctypes.c_byte),
        ('next', ctypes.c_void_p),
    ]

class KrkValueAs(ctypes.Union):
    _fields_ = [
        ('boolean', ctypes.c_byte),
        ('integer', ctypes.c_long), # Or `long long`, really need to check the lib at runtime...
        ('floating', ctypes.c_double),
        ('handler', KrkJumpTarget),
        ('object', ctypes.POINTER(KrkObj)),
    ]

class KrkValue(ctypes.Structure):
    _fields_ = [
        ('type_', ctypes.c_int),
        ('as_', KrkValueAs),
    ]

class KrkTableEntry(ctypes.Structure):
    _fields_ = [
        ('key', KrkValue),
        ('value', KrkValue),
    ]

class KrkTable(ctypes.Structure):
    _fields_ = [
        ('count', ctypes.c_size_t),
        ('capacity', ctypes.c_size_t),
        ('entries', ctypes.POINTER(KrkTableEntry)),
    ]

class KrkString(ctypes.Structure):
    _fields_ = [
        ('obj', KrkObj),
        ('type_', ctypes.c_int),
        ('hash', ctypes.c_uint32),
        ('length', ctypes.c_size_t),
        ('codesLength', ctypes.c_size_t),
        ('chars', ctypes.c_char_p),
        ('codes', ctypes.c_void_p),
    ]

class KrkClass(ctypes.Structure):
    _fields_ = [
        ('obj', KrkObj),
        ('name', ctypes.POINTER(KrkString)),
        ('filename', ctypes.POINTER(KrkString)),
        ('docstring', ctypes.POINTER(KrkString)),
        ('base', ctypes.POINTER(KrkObj)),
        ('methodTable', KrkTable),
        ('fieldTable', KrkTable),
        ('allocSize', ctypes.c_size_t),
        ('_ongcscan', ctypes.c_void_p),
        ('_ongcsweep', ctypes.c_void_p),
        ('_getter', ctypes.POINTER(KrkObj)),
        ('_setter', ctypes.POINTER(KrkObj)),
        ('_slicer', ctypes.POINTER(KrkObj)),
        ('_reprer', ctypes.POINTER(KrkObj)),
        ('_tostr', ctypes.POINTER(KrkObj)),
        ('_call', ctypes.POINTER(KrkObj)),
        ('_init', ctypes.POINTER(KrkObj)),
        ('_eq', ctypes.POINTER(KrkObj)),
        ('_len', ctypes.POINTER(KrkObj)),
        ('_enter', ctypes.POINTER(KrkObj)),
        ('_exit', ctypes.POINTER(KrkObj)),
        ('_delitem', ctypes.POINTER(KrkObj)),
        ('_iter', ctypes.POINTER(KrkObj)),
        ('_getattr', ctypes.POINTER(KrkObj)),
        ('_dir', ctypes.POINTER(KrkObj)),
    ]

class KurokoVM(object):
    def __init__(self,libraryPath='./libkuroko.so'):
        self.lib = ctypes.CDLL('./libkuroko.so', mode=ctypes.RTLD_GLOBAL)
        self.lib.krk_initVM();
        self.startModule = self.lib.krk_startModule
        self.startModule.argtypes = [ctypes.c_char_p]
        self.startModule.restype = ctypes.c_void_p # Don't care for now.
        self.startModule(b"<jupyter>")
        self.interpret = self.lib.krk_interpret
        self.interpret.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_char_p]
        self.interpret.restype = KrkValue
        self.push = self.lib.krk_push
        self.push.argtypes = [KrkValue]
        self.pop = self.lib.krk_pop
        self.pop.restype = KrkValue
        self.getType = self.lib.krk_getType
        self.getType.argtypes = [KrkValue]
        self.getType.restype = ctypes.POINTER(KrkClass)
        self.callSimple = self.lib.krk_callSimple
        self.callSimple.argtypes = [KrkValue, ctypes.c_int, ctypes.c_int]
        self.callSimple.restype = KrkValue
        #self.interpret(b'set_tracing(tracing=1)\n',0,b'<jupyter>',b'<stdin>')

    def reprVal(self, value):
        self.push(value)
        classObj = self.getType(value)
        reprAsValue = KrkValue(type_=KrkValueType.VAL_OBJECT,as_=KrkValueAs(object=classObj.contents._reprer))
        reprResult = self.callSimple(reprAsValue, 1, 0)
        self.lib.krk_resetStack()
        if reprResult.type_ != KrkValueType.VAL_OBJECT or (reprResult.as_.object).contents.type_ != ObjType.OBJ_STRING:
            return ValueError("Invalid.")
        else:
            return ctypes.cast(reprResult.as_.object, ctypes.POINTER(KrkString)).contents.chars.decode()

    def call(self, code):
        result = self.interpret(code.encode(),0,b"<jupyter>",b"<stdin>")
        if result.type_ == KrkValueType.VAL_NONE:
            return None
        else:
            return self.reprVal(result)

class KurokoKernel(Kernel):
    implementation = 'Kuroko'
    implementation_version = '1.0'
    language = 'kuroko'
    language_version = '1.0.0-rc0' # TODO read from .so?
    language_info = {
        'name': 'kuroko',
        'mimetype': 'text/x-kuroko',
        'file_extension': '.krk',
        'codemirror_mode': 'Python',
        'pygments_lexer': 'kuroko',
    }
    banner = 'Kuroko Jupyter Kernel'

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.vm = KurokoVM()

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        response = self.vm.call(code)
        if response is not None:
            self.send_response(self.iopub_socket, 'execute_result', {'execution_count': self.execution_count, 'data': {'text/plain': response}})
        return {'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
        }

    def do_is_complete(self, code):
        def isComplete(code):
            if not code.strip(): return True
            lines = code.split('\n')
            if not lines[-1].strip(): return True
            if code[-1] == ':' or len(lines) > 1: return False
            return True
        def getSpaces(s):
            count = 0
            for c in s:
                if c == ' ':
                    count += 1
                else:
                    break
            return ' ' * count
        if isComplete(code):
            return {'status': 'complete'}
        else:
            indent = getSpaces(code.split('\n')[-1])
            if code[-1] == ':':
                indent += '    '
            return {'status': 'incomplete', 'indent': indent}

if __name__ == '__main__':
    import sys
    if sys.argv[-1] == '--shit':
        vm = KurokoVM()
        print(vm.call('1+2'))
    else:
        from ipykernel.kernelapp import IPKernelApp
        IPKernelApp.launch_instance(kernel_class=KurokoKernel)

