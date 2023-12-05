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
from ..interpreterbase import typed_kwargs, typed_pos_args, KwargInfo 

from .. import build
from ..mesonlib import File, Popen_safe, MesonException
    
if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter.interpreter import Interpreter
    from ..interpreterbase.baseobjects import TYPE_kwargs, TYPE_var
    from ..programs import ExternalProgram

class FilamentModule(NewExtensionModule):

    INFO = ModuleInfo('filament')

    def __init__(self, interp: Interpreter) -> None:
        super().__init__()
        self.exe: T.Union[ExternalProgram, build.Executable] = None
        self.include_dir = None
        self.methods.update({
            'generate': self.generate
        })

    @typed_pos_args('filament.generate', str, (str, File))
    @typed_kwargs('filament.generate', KwargInfo('lib', (str, File)))    
    def generate(self, state: ModuleState, args: T.Tuple[str, FileOrString], kwargs: TYPE_kwargs) -> None:
        if not self.exe:
            self.exe = state.find_program('filament')

        proj_name, arg_src = args
        lib = kwargs['lib']

        # output: T.List[build.GeneratedList] = []

        # moc_gen = build.Generator(
        #     self.exe, ['-l', lib, '@INPUT@'], ['@BASENAME@.sv'],
        #     capture=True,
        #     name=f'Filament verilog')
        # output.append(moc_gen.process_files([arg_src], state))

        # moc_gen = build.Generator(
        #     self.exe, ['-l', lib, '--dump-interface', '@INPUT@'], ['@BASENAME@.it'],
        #     capture=True,
        #     name=f'Filament interface')
        # output.append(moc_gen.process_files([arg_src], state))


        # return ModuleReturnValue(output, [output])

        # depfile = File.from_built_file(path.get_subdir(), path.get_filename())
        #     data = File.from_source_file(state.environment.source_dir, state.subdir, data)
        # depfile = state._interpreter.source_strings_to_files(
        #     ))
        sv_target = build.CustomTarget(
            f'{proj_name}_sv',
            state.subdir,
            state.subproject,
            state.environment,
            [self.exe, '@INPUT@', '-l', lib, '--out', '@OUTPUT0@', '--dump-interface-file', '@OUTPUT1@', '--dump-dep-file', '@DEPFILE@'],
            [arg_src],
            # [f'{proj_name}.sv', f'{proj_name}.it', dep_file],
            [f'{proj_name}.sv', f'{proj_name}.it'],
            depfile=f'{proj_name}.d',
            capture=True
        )

        return ModuleReturnValue(sv_target, [sv_target])

def initialize(interp: Interpreter) -> FilamentModule:
    return FilamentModule(interp)
