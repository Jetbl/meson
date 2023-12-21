# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import typing as T
import subprocess, shutil

from . import NewExtensionModule, ModuleReturnValue, ModuleInfo
from ..interpreterbase import typed_kwargs, typed_pos_args, KwargInfo, noKwargs, noPosargs

from .. import build
from ..mesonlib import File, Popen_safe, MesonException
    
if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter.interpreter import Interpreter
    from ..interpreterbase.baseobjects import TYPE_kwargs, TYPE_var
    from ..programs import ExternalProgram

class RsrtlModule(NewExtensionModule):

    INFO = ModuleInfo('rsrtl')

    def __init__(self, interp: Interpreter) -> None:
        super().__init__()
        self.tools: T.Dict[str, T.Union[ExternalProgram, build.Executable]] = {}
        self.include_dir = None
        self.methods.update({
            'generate': self.generate,
            'get_includes': self.get_includes,
        })


    def detect_tools(self, state: ModuleState) -> None:
        self.tools['yosys'] = state.find_program('yosys')

    @typed_pos_args('rsrtl.generate', str, (str, File, build.CustomTarget, build.CustomTargetIndex, build.GeneratedList))
    @typed_kwargs('rsrtl.generate', KwargInfo('script', str, default='hierarchy -top main; write_cxxrtl -print-output std::cerr @OUTPUT@'), KwargInfo('tcl', bool, default=False), KwargInfo('header', bool, default=False))
    def generate(self, state: ModuleState, args: T.Tuple[str, T.List[T.Union[FileOrString, build.GeneratedTypes]]], kwargs: TYPE_kwargs) -> None:
        if not self.tools:
            self.detect_tools(state)
        proj_name, arg_src = args
        script = kwargs['script']
        header = kwargs['header']
        tcl = script.endswith('.tcl')
        output = f'{proj_name}.cc'
        output_header = f'{proj_name}.h'

        if tcl:
            if isinstance(script, str):
                script = File.from_source_file(state.source_root, state.subdir, script)

            cmd = [self.tools['yosys'], '-q', '-p', f"tcl {script.rel_to_builddir(state.build_to_src)} {output} @INPUT@"]
            depend_files = [script]
        else:
            cmd = [self.tools['yosys'], '-q', '-p', script, '@INPUT@']
            depend_files = []

        outputs = [f'{output}', f'{output_header}'] if header else [f'{output}']

        cc_target = build.CustomTarget(
            f'{proj_name}',
            state.subdir,
            state.subproject,
            state.environment,
            cmd,
            [arg_src],
            outputs,
            depend_files=depend_files
        )

        return ModuleReturnValue(cc_target, [cc_target])

    def get_include_dir(self, state: ModuleState) -> str:
        if not self.include_dir:
            if not self.tools:
                self.detect_tools(state)

            cmd = [shutil.which('yosys-config'), '--datdir/include']
            p, o, e = Popen_safe(cmd, stdout=subprocess.PIPE)
            if p.returncode != 0:
                raise MesonException('yosys-config command failed')
            self.include_dir = o.strip()

        return self.include_dir 

    @noKwargs
    @noPosargs
    def get_includes(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.get_include_dir(state)

def initialize(interp: Interpreter) -> RsrtlModule:
    return RsrtlModule(interp)
