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
from ..interpreterbase import typed_kwargs, typed_pos_args, KwargInfo, ContainerTypeInfo 

from .. import build
from ..mesonlib import File, Popen_safe, MesonException, EnvironmentVariables, relpath

from os import path

from mesonbuild.cargo.interpreter import _load_manifests
    
if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter.interpreter import Interpreter
    from ..interpreterbase.baseobjects import TYPE_kwargs, TYPE_var
    from ..programs import ExternalProgram

class CargoModule(NewExtensionModule):

    INFO = ModuleInfo('cargo')

    def __init__(self, interp: Interpreter) -> None:
        super().__init__()
        self.exe: T.Union[ExternalProgram, build.Executable] = None
        self.include_dir = None
        self.methods.update({
            'staticlib': self.staticlib,
            'executable': self.executable
        })

    @typed_pos_args('cargo.staticlib', (str, File), str)
    @typed_kwargs('cargo.staticlib', KwargInfo('profile', str, default='dev'))    
    def staticlib(self, state: ModuleState, args: T.Tuple[FileOrString, str], kwargs: TYPE_kwargs) -> None:
        if not self.exe:
            self.exe = state.find_program('cargo')

        manifest, libname = args
        subdir = path.abspath(path.dirname(manifest)) 
        # subdir = relpath (path.dirname(manifest), state.source_root) 
        profile = kwargs['profile']

        # lib = _load_manifests(subdir)[libname].lib

        # if not 'staticlib' in lib.crate_type:
        #     raise MesonException("not staticlib")

        target = path.join(state.subdir, f'{libname}_target')
        staticlib = path.join(target, 'debug' if profile == 'dev' else 'release', f'lib{libname}.a')
        depfile = path.join(target, 'debug' if profile == 'dev' else 'release', f'lib{libname}.d')

        cargo_target = build.CustomTarget(
            f'{libname}_cargo_build',
            state.subdir,
            state.subproject,
            state.environment,
            [self.exe, 'build', '--lib', '--manifest-path', '@INPUT@', '--target-dir', target, '--profile', profile],
            [manifest],
            [staticlib],
            depfile=depfile
        )

        return ModuleReturnValue(cargo_target, [cargo_target])

    @typed_pos_args('cargo.executable', (str, File), str)
    @typed_kwargs('cargo.executable', KwargInfo('profile', str, default='dev'), KwargInfo('link_with',  ContainerTypeInfo(list, (build.SharedLibrary, build.StaticLibrary)), listify=True, default=[])) 
    def executable(self, state: ModuleState, args: T.Tuple[FileOrString, str], kwargs: TYPE_kwargs) -> None:
        if not self.exe:
            self.exe = state.find_program('cargo')

        subdir, manifest= args
        profile = kwargs['profile']
        link_with= kwargs['link_with']

        m = _load_manifests(subdir)
        bins = _load_manifests(subdir)[manifest].bin

        bin = None
        for b in bins:
            if b.name == manifest:
                bin = b
                break

        if not bin:
            raise MesonException(f"{manifest} not find")

        target = path.join(state.subdir, f'{bin.name}_target')
        exe = path.join(target, 'debug' if profile == 'dev' else 'release', bin.name)
        depfile = path.join(target, 'debug' if profile == 'dev' else 'release', f'{bin.name}.d')

        link_flags = ''
        for lib in link_with:
            libdir = path.join(state.environment.get_build_dir(), state.backend.get_target_dir(lib))
            link_flags += f'-L {libdir} -l{lib.name}'

        env = EnvironmentVariables({'RUSTFLAGS': link_flags})

        cargo_target = build.CustomTarget(
            f'{bin.name}_cargo_exe_build',
            state.subdir,
            state.subproject,
            state.environment,
            [self.exe, 'build', '--bin', bin.name, '--manifest-path', '@INPUT@', '--target-dir', target, '--profile', profile],
            [f'{subdir}/Cargo.toml'],
            [exe],
            depfile=depfile,
            extra_depends= link_with,
            env=env
        )

        return ModuleReturnValue(cargo_target, [cargo_target])

def initialize(interp: Interpreter) -> CargoModule:
    return CargoModule(interp)
