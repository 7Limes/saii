# Simple App Image Installer v1.0.0
# By Miles Burkart
#
# This script does 4 things:
# 1. Enables execution permission on the AppImage
# 2. Moves the AppImage to ~/.local/bin
# 3. Creates a .desktop file in ~/.local/share/applications
# 4. Adds icons to ~/.local/share/icons

import sys
import os
import subprocess
import shutil
from pathlib import Path
import stat
from argparse import ArgumentParser
from PIL import Image


WORK_PATH = Path('/tmp/saii')
INSTALL_PATH = Path('~/.local/bin').expanduser()

DESKTOP_SUFFIX = '.desktop'

# Paths where the .desktop file might be
SQUASHFS_DESKTOP_FILE_PATHS = [
    Path('squashfs-root'),
    Path('squashfs-root/share/applications'),
    Path('squashfs-root/usr/share/applications'),
]

# Paths where icons might be
# Contains a directory and a boolean to indicate recursive search
SQUASHFS_ICONS_PATHS = [
    (Path('squashfs-root'), False),
    (Path('squashfs-root/share/icons'), True),
    (Path('squashfs-root/usr/share/icons'), True)
]

USER_DESKTOP_FILE_PATH = Path('~/.local/share/applications').expanduser()
USER_ICONS_PATH = Path('~/.local/share/icons/hicolor').expanduser()


def print_error(message: str):
    print(message, file=sys.stderr)


def is_appimage(path: str) -> bool:
    """
    Returns True if the given file is an AppImage
    """
    if not os.path.isfile(path):
        return False

    with open(path, 'rb') as f:
        header = f.read(12)
    
    if len(header) < 12:
        return False
    
    if header[:4] != b'\x7fELF':
        return False
    
    if header[8:10] == b'AI' and header[10] in (0x01, 0x02):
        return True
    
    return False


def find_desktop_file() -> Path:
    """
    Tries to locate the .desktop file in the squashfs directory
    """
    for directory in SQUASHFS_DESKTOP_FILE_PATHS:
        full_directory_path = WORK_PATH / directory
        directory_files = (x for x in full_directory_path.glob('*') if x.is_file())
        for file in directory_files:
            if file.suffix == DESKTOP_SUFFIX:
                return full_directory_path / file
    
    raise FileNotFoundError('Could not find .desktop file')


def find_icons(icon_name: str) -> list[Path]:
    """
    Tries to locate app icons in the squashfs directory
    """
    icon_paths: list[Path] = []

    for directory, do_recursive in SQUASHFS_ICONS_PATHS:
        full_directory_path = WORK_PATH / directory
        if not full_directory_path.exists():
            continue

        if do_recursive:
            for root, _, files in os.walk(full_directory_path):
                root_path = Path(os.path.abspath(root))
                for file in files:
                    name, ext = os.path.splitext(file)
                    if ext == '.png' and name == icon_name:
                        icon_paths.append(root_path / file)
        else:
            directory_files = (x for x in full_directory_path.glob('*') if x.is_file())
            for file in directory_files:
                if file.suffix == '.png':
                    icon_paths.append(full_directory_path / file)

    return icon_paths


def install_appimage(appimage_path: str) -> int:
    if not os.path.isfile(appimage_path):
        print_error('File not found')
        return 1
    
    if not is_appimage(appimage_path):
        print_error('The provided file is not an AppImage')
        return 2

    if not os.path.exists(WORK_PATH):
        os.mkdir(WORK_PATH)
    
    appimage_abspath = os.path.abspath(appimage_path)

    # Extract the AppImage
    print('Extracting AppImage...')
    extract_cmd = [
        appimage_abspath, '--appimage-extract'
    ]
    try:
        subprocess.run(extract_cmd, cwd=WORK_PATH, stdout=subprocess.DEVNULL)
    except Exception as e:
        print_error('Got error during AppImage extraction: ' + str(e))
        return 3
    
    # Move the AppImage to install directory
    installed_app_path = shutil.move(appimage_abspath, INSTALL_PATH)

    # Make AppImage executable
    installed_app_path = Path(installed_app_path)
    current_permissions = installed_app_path.stat().st_mode
    installed_app_path.chmod(current_permissions | stat.S_IXUSR)

    # Edit .desktop file and copy to home folder
    print('Creating .desktop file...')
    desktop_file_path = find_desktop_file()
    with open(desktop_file_path, 'r') as f:
        desktop_file_lines = f.readlines()
    
    for i, desktop_line in enumerate(list(desktop_file_lines)):
        if desktop_line.startswith('Exec='):
            desktop_file_lines[i] = f'Exec={installed_app_path}\n'
        elif desktop_line.startswith('TryExec='):
            desktop_file_lines[i] = f'TryExec={installed_app_path}\n'
        elif desktop_line.startswith('Icon='):
            desktop_icon_name = desktop_line.strip().removeprefix('Icon=')
    
    with open(USER_DESKTOP_FILE_PATH / desktop_file_path.name, 'w') as f:
        f.writelines(desktop_file_lines)
    
    # Copy icons to home folder
    print('Copying icons...')
    icon_paths = find_icons(desktop_icon_name)
    for icon_path in icon_paths:
        img = Image.open(icon_path)
        width, height = img.size
        img.close()
        write_directory = USER_ICONS_PATH / f'{width}x{height}' / 'apps'
        write_path = write_directory / icon_path.name
        write_directory.mkdir(parents=True, exist_ok=True)
        shutil.copy(icon_path, write_path)

    # Cleanup
    shutil.rmtree(WORK_PATH)

    print(f'Installed AppImage at {installed_app_path}')

    return 0


def main() -> int:
    parser = ArgumentParser('saii', description='Simple AppImage Installer')
    parser.add_argument('appimage_path', type=str, help='The AppImage to install')

    args = parser.parse_args()

    return install_appimage(args.appimage_path)


if __name__ == '__main__':
    sys.exit(main())
