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
from ..interpreterbase import typed_kwargs, typed_pos_args, noKwargs

from .. import build
from ..mesonlib import File, Popen_safe, MesonException
from os import path
    
if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter.interpreter import Interpreter
    from ..interpreterbase.baseobjects import TYPE_kwargs, TYPE_var
    from ..programs import ExternalProgram

class CxxModule(NewExtensionModule):

    INFO = ModuleInfo('cxx')

    def __init__(self, interp: Interpreter) -> None:
        super().__init__()
        self.exe: T.Union[ExternalProgram, build.Executable] = None
        self.include_dir = None
        self.methods.update({
            'generate': self.generate
        })

    @typed_pos_args('cxx.generate', str, (str, File))
    @noKwargs
    def generate(self, state: ModuleState, args: T.Tuple[str, FileOrString], kwargs: TYPE_kwargs) -> None:
        if not self.exe:
            self.exe = state.find_program('cxxbridge')

        proj_name, bridge_src = args

        rh = path.join(state.subdir, 'rust', 'cxx.h')
        rh_target = build.CustomTarget(
            f'{proj_name}_cxx_rh',
            state.subdir,
            state.subproject,
            state.environment,
            [self.exe, '--header'],
            [bridge_src],
            [rh],
            capture=True
        )

        h_target = build.CustomTarget(
            f'{proj_name}_cxx_h',
            state.subdir,
            state.subproject,
            state.environment,
            [self.exe, '@INPUT@', '--header'],
            [bridge_src],
            [f'{proj_name}.h'],
            capture=True
        )

        cc_target = build.CustomTarget(
            f'{proj_name}_cxx_cc',
            state.subdir,
            state.subproject,
            state.environment,
            [self.exe, '@INPUT@'],
            [bridge_src],
            [f'{proj_name}.cc'],
            extra_depends=[h_target],
            capture=True
        )

        return ModuleReturnValue([rh_target, h_target, cc_target], [rh_target, h_target, cc_target])

def initialize(interp: Interpreter) -> CxxModule:
    return CxxModule(interp)
