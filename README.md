## What it is/does

Google-Streetview-DL is a python rewrite of [streetview-dl](https://github.com/fdd4s/streetview-dl) which aims to fix some known bugs, and potential future issues with sections of the codebase

It *should* grab the highest resolution available for the given panorama, then stitches the result into a proper equirectangular image.

## Dependencies

python, aria2, imagemagick, exiftool, Pillow (optional)

The original script, and this rewrite were designed to run on Linux, but Windows and MacOS should also work, given the proper dependencies are installed.

HOWEVER it is important to note that I have not tested Windows support, and that any Windows testing would've been several months ago by now

## How to use

Little warning that this might violate google maps ToS

Linux:
	
	$ gsvdl.py <url provided with quotes>

Windows:
	
	$ python gsvdl.py <url provided with quotes>

Just a reminder that Windows support has not been thoroughly tested, since I cba to setup the dependencies on my vm lol

## Known Issues / To do

"montage-im6.q16: cache resources exhausted " can be resolved changing ImageMagick configuration, more info here: [ImageMagick Issue #396](https://github.com/ImageMagick/ImageMagick/issues/396)

Aside from that, there aren't any *currently* known issues. Just some rewrites that should be made in the interest of keeping this thing working if google decides to randomly change something, which is pretty common

## Credits

Original script creator - [fdd4s](https://github.com/fdd4s)

Python rewrite - [chloezu](https://github.com/chloezu)

Helped clean up my code a little - [Seloris](https://github.com/allocazione)
