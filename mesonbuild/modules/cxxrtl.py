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

class CxxrtlModule(NewExtensionModule):

    INFO = ModuleInfo('cxxrtl')

    def __init__(self, interp: Interpreter) -> None:
        super().__init__()
        self.tools: T.Dict[str, T.Union[ExternalProgram, build.Executable]] = {}
        self.include_dir = None
        self.methods.update({
            'generate': self.generate,
            'sim': self.sim,
            'get_sources': self.get_sources,
            'get_includes': self.get_includes,
        })

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

    def detect_tools(self, state: ModuleState) -> None:
        self.tools['yosys'] = state.find_program('yosys')
        self.tools['cxxrtl-driver'] = state.find_program('cxxrtl-driver')

    @typed_pos_args('cxxrtl.generate', str, (str, File, build.CustomTarget, build.CustomTargetIndex, build.GeneratedList))
    @typed_kwargs('cxxrtl.generate', KwargInfo('script', (str, File), default='hierarchy -top main; write_cxxrtl -O0 -print-output std::cerr @OUTPUT@'))    
    def generate(self, state: ModuleState, args: T.Tuple[str, T.List[T.Union[FileOrString, build.GeneratedTypes]]], kwargs: TYPE_kwargs) -> None:
        if not self.tools:
            self.detect_tools(state)
        proj_name, arg_src = args
        script = kwargs['script']

        cc_target = build.CustomTarget(
            f'{proj_name}_cc',
            state.subdir,
            state.subproject,
            state.environment,
            [self.tools['yosys'], '-q', '-p', script, '@INPUT@'],
            [arg_src],
            [f'{proj_name}.cc'],
        )

        return ModuleReturnValue(cc_target, [cc_target])

    @typed_pos_args('cxxrtl.sim', str, (str, File, build.BuildTarget))
    @typed_kwargs('cxxrtl.sim', KwargInfo('data', (str, File)), KwargInfo('interface', (str, File, build.CustomTarget, build.CustomTargetIndex, build.GeneratedList)), KwargInfo('vcd', bool, default=False))
    def sim(self, state: ModuleState, args: T.Tuple[str, T.Union[FileOrString, build.BuildTargetTypes]], kwargs: TYPE_kwargs) -> None:
        if not self.tools:
            self.detect_tools(state)

        proj_name, design = args
        data = kwargs['data']
        interface = kwargs['interface']
        vcd = kwargs['vcd']

        if isinstance(data, str):
            data = File.from_source_file(state.environment.source_dir, state.subdir, data)

        if isinstance(interface, str):
            interface= File.from_source_file(state.environment.source_dir, state.subdir, interface)

        if isinstance(interface, build.GeneratedList):
            s = interface.get_outputs()[0]
            rel_src = state.backend.get_target_generated_dir(self, interface, s)
            interface = File.from_built_relative(rel_src)

        cmd_array = [self.tools['cxxrtl-driver'], '--design', design, '--data', data, '--interface', interface]
        if vcd:
            cmd_array.push('--vcd')
        
        out_target= build.CustomTarget(
            f'{proj_name}_sim',
            state.subdir,
            state.subproject,
            state.environment,
            cmd_array,
            [],
            [f'{proj_name}.sim'],
            capture=True
        )

        return ModuleReturnValue(out_target,  [out_target])

    @noKwargs
    @noPosargs
    def get_sources(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return "{}/backends/cxxrtl/cxxrtl_capi.cc".format(self.get_include_dir(state))

    @noKwargs
    @noPosargs
    def get_includes(self, state: ModuleState, args: T.List[TYPE_var], kwargs: TYPE_kwargs) -> str:
        return self.get_include_dir(state)

def initialize(interp: Interpreter) -> CxxrtlModule:
    return CxxrtlModule(interp)
