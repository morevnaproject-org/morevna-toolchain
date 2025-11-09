#!python3

import os
import sys
import re
from subprocess import run
import platform

MOREVNATOOLCHAIN_VERSION = '0.7'

def compare_versions(v1, v2):
    v1 = re.sub(r'-', '.', v1)
    v2 = re.sub(r'-', '.', v2)
    v1_parts = list(map(int, v1.split('.')))
    v2_parts = list(map(int, v2.split('.')))
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts += [0] * (max_len - len(v1_parts))
    v2_parts += [0] * (max_len - len(v2_parts))
    for i in range(max_len):
        if v1_parts[i] > v2_parts[i]:
            return '>'
        elif v1_parts[i] < v2_parts[i]:
            return '<'
    return '='

def compare_versions2(v1, v2):
    v1 = re.sub(r'-', '.', v1)
    v2 = re.sub(r'-', '.', v2)

    ver1 = list(map(int, v1.split('.')))
    ver2 = list(map(int, v2.split('.')))

    for i in range(max(len(ver1), len(ver2))):
        if i >= len(ver1):
            ver1 += [0]
        if i >= len(ver2):
            ver2 += [0]

        if ver1[i] > ver2[i]:
            return ">"
        if ver1[i] < ver2[i]:
            return "<"

    return "="

def find_version(testdir, app):
    envfile = ''
    if os.path.exists(os.path.join(testdir, 'env.txt')):
        envfile = 'env.txt'
    elif os.path.exists(os.path.join(testdir, 'packages.txt')):
        envfile = 'packages.txt'
    if envfile:
        with open(os.path.join(testdir, envfile), 'r') as f:
            for line in f:
                package, version = line.split('=')
                if package.strip() == app:
                    return version.strip()
        return find_version(os.path.dirname(testdir), app)
    else:
        if testdir == '/':
            return None
        return find_version(os.path.dirname(testdir), app)

def exec_app(app, *args):

    MOREVNATOOLCHAIN_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ['PATH'] = os.path.join(MOREVNATOOLCHAIN_DIR, 'bin') + ':' + os.environ.get('PATH', '')
    #os.environ['MOREVNATOOLCHAIN_PATH_IS_SET'] = '1'

    USE_0INSTALL = 0
    
    config_files = [
        os.path.join(MOREVNATOOLCHAIN_DIR,"etc","morevna-toolchain.ini"),
        os.path.join(os.path.expanduser('~'),".config","morevna-toolchain","morevna-toolchain.ini")
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                for line in f:
                    if line.strip().startswith("export "):
                        print(line)
                        key, value = line.strip().split("=")
                        if key=="USE_0INSTALL":
                            USE_0INSTALL = int(value.strip()[1:-1])
                        print(key)

    cache_dir = os.environ.get("MOREVNATOOLCHAIN_CACHEDIR")
    if cache_dir:
        os.environ["ZEROINSTALL_PORTABLE_BASE"] = cache_dir
    
    # Autoupdate configuration (Linux only ATM)
    #if platform.system() == "Linux":
    #    version_file=os.path.join(os.path.expanduser('~'), '.config', 'morevna-toolchain', 'morevna-toolchain.version')
    #    if os.path.exists(version_file):
    #        with open(version_file, 'r') as f:
    #            for line in f:
    #                if line.startswith('MOREVNATOOLCHAIN_INSTALLED_VERSION='):
    #                    installed_version = line.split('=')[1].strip()
    #                    if installed_version != MOREVNATOOLCHAIN_VERSION:
    #                        if os.path.exists(os.path.join(MOREVNATOOLCHAIN_DIR, 'lib', 'morevna-toolchain', 'user-install')):
    #                            run([os.path.join(MOREVNATOOLCHAIN_DIR, 'lib', 'morevna-toolchain', 'user-install')])
    
    #app_name_uppercase=app.upper()

    binary=""
    if len(app.split("/"))==1:
        binary = app
        binary_0install_option = 'run'
    else:
        binary = app.split("/")[1]
        app = app.split("/")[0]
        # We can call alternative binary via "--command" option.
        # See - https://docs.0install.net/specifications/feed/#commands
        binary_0install_option = binary
    
    URI_0INSTALL=""
    EXTENSIONS=[]
    conf_file = os.path.join(MOREVNATOOLCHAIN_DIR, 'share', 'morevna-toolchain', 'packages', app + '.conf')
    if os.path.exists(conf_file):
        with open(conf_file, 'r') as f:
            for line in f:
                if line.startswith('URI_0INSTALL='):
                    URI_0INSTALL = line.split('=')[1].strip()
                elif line.startswith('EXTENSIONS='):
                    EXTENSIONS = line.split('=')[1].strip()[1:-1].split(" ")
    
    # find which file we are working with
    arg_file = ''
    for arg in args:
        for ext in EXTENSIONS:
            if arg.endswith('.' + ext):
                arg_file = arg
                break
        if arg_file:
            break
    
    # find package version defined for this file
    if arg_file:
        arg_file_dirname = os.path.dirname(arg_file)
        app_version = find_version(arg_file_dirname, app)
    else:
        app_version = find_version(os.getcwd(), app)
        
    print(app_version)
    # a. If version is not empty
    #  - ini configuration
    #  - /opt/package-version
    #  - 0install
    # b. If version is empty
    #  - ini configuration
    #  - /opt/package
    #  - 0install
    #  - /opt/package-version (latest) (fallback)
    
    found = 0
    if app_version:
        # 1. Read ini configuration
        if os.path.exists(os.path.join(MOREVNATOOLCHAIN_DIR, 'etc', 'morevna-toolchain.d', app + '.ini')):
            app_path = ''
            with open(os.path.join(MOREVNATOOLCHAIN_DIR, 'etc', 'morevna-toolchain.d', app + '.ini'), 'r') as f:
                for line in f:
                    version, path = line.split('=')
                    if version.strip() == app_version:
                        app_path = path.strip()
                        break
            # TODO: On Windows check for .bat or .exe
            if app_path:
                app_path = os.path.join(app_path, binary)
                if os.path.exists(app_path) and os.access(app_path, os.X_OK):
                    found = 1
                    run([app_path] + list(args))
        
        # 2. Check packages in opt
        if found != 1:
            app_dir = app+"-"+app_version
            for optdir in [os.path.join(MOREVNATOOLCHAIN_DIR, 'opt'), '/opt']:
                app_path = os.path.join(optdir, app_dir, binary)
                if os.path.exists(app_path) and os.access(app_path, os.X_OK):
                    found = 1
                    run([app_path] + list(args))
                    break

        # 3. Use 0-install
        if found != 1 and USE_0INSTALL == 1 and URI_0INSTALL != "":
            version_option = f'--version={app_version}'
            found = 1
            run(['0install', 'run', version_option, f'--command={binary_0install_option}', URI_0INSTALL] + list(args))

    else:  # app_version is undefined - use latest/default version
        # 1. Read ini configuration
        if os.path.exists(os.path.join(MOREVNATOOLCHAIN_DIR, 'etc', 'morevna-toolchain.d', app + '.ini')):
            app_version = 'DEFAULT'
            app_path = ''
            with open(os.path.join(MOREVNATOOLCHAIN_DIR, 'etc', 'morevna-toolchain.d', app + '.ini'), 'r') as f:
                for line in f:
                    version, path = line.split('=')
                    if version.strip() == app_version:
                        app_path = path.strip()
                        break
            if app_path:
                app_path = os.path.join(app_path, binary)
                if os.path.exists(app_path) and os.access(app_path, os.X_OK):
                    found = 1
                    run([app_path] + list(args))
        
        # 2. Check packages in opt
        if found != 1:
            for optdir in [os.path.join(MOREVNATOOLCHAIN_DIR, 'opt'), '/opt']:
                app_path = os.path.join(optdir, app, binary)
                if os.path.exists(app_path) and os.access(app_path, os.X_OK):
                    found = 1
                    run([app_path] + list(args))
                    break
        
        # 3. Use 0-install
        if found != 1 and USE_0INSTALL == 1 and URI_0INSTALL != "":
            found = 1
            run(['0install', 'run', f'--command={binary_0install_option}', URI_0INSTALL] + list(args[1:]))
        
        # 4. Use latest installed version
        if found != 1:
            latest_version = '0'
            latest_version_path = ''
            if os.path.exists(os.path.join(MOREVNATOOLCHAIN_DIR, 'etc', 'morevna-toolchain.d', app + '.ini')):
                with open(os.path.join(MOREVNATOOLCHAIN_DIR, 'etc', 'morevna-toolchain.d', app + '.ini'), 'r') as f:
                    for line in f:
                        path = line.split('=')[1].strip()
                        if os.path.exists(path) and os.access(path, os.X_OK):
                            version = line.split('=')[0].strip()
                            if version != 'DEFAULT':
                                result = compare_versions(latest_version, version)
                                if result == '<':
                                    latest_version = version
                                    latest_version_path = path
            for optdir in [os.path.join(MOREVNATOOLCHAIN_DIR, 'opt'), '/opt']:
                for dir in os.listdir(optdir):
                    path_dir = os.path.join(optdir, dir)
                    if os.path.isdir(path_dir) and dir.startswith(app + "-"):
                        version = dir.split('-')[-1]
                        result = compare_versions(latest_version, version)
                        if result == '<':
                            latest_version = version
                            latest_version_path = app_path
            if latest_version_path:
                found = 1
                run([latest_version_path] + list(args[1:]))
    
    if found != 1:
        print(f"ERROR: Unable to find any installation of '{app}'.")
        print(f"       Please make sure to add following line to")
        print(f"       '{MOREVNATOOLCHAIN_DIR}/etc/morevna-toolchain.d/{app}.ini':")
        print()
        print(f"              {app.upper()}_DEFAULT=\"/path/to/app/binary\"")
        print()
        sys.exit(1)

def usage():
    print("""
=============================================================
Morevna Toolchain - software manager for animation production
=============================================================

Usage:
    morevna-toolchain exec APP [ARGS]

Examples:
    morevna-toolchain exec blender
    morevna-toolchain exec blender --help
    MOREVNA_VERSION_BLENDER=2.78-1 morevna-toolchain exec blender
""")

def main():
    
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    
    if sys.argv[1] == 'exec':
        if len(sys.argv) < 3:
            usage()
            sys.exit(1)
        exec_app(sys.argv[2], *sys.argv[3:])
    else:
        usage()
        sys.exit(1)

if __name__ == '__main__':
    main()
