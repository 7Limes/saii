# saii

A Simple AppImage Installer


## This script does 4 things:

1. Enables execution permission on the AppImage
2. Moves the AppImage to ~/.local/bin
3. Creates a .desktop file in ~/.local/share/applications
4. Adds icons to ~/.local/share/icons


## Usage

```sh
python3 saii.py [appimage_path]
```