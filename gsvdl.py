#!/bin/python3

#-------------------------------------------#
#                  Credits                  #
#-------------------------------------------#
# fdd4s for the idea, code structure        #
#               and php base                #
# https://github.com/fdd4s/streetview-dl    #
#-------------------------------------------#
# Exterpolation for making my code readable #
# https://github.com/exterpolation          #
#-------------------------------------------#
# Chloezu [me], functional but crappy       #
# python rewrite of fdd4s' script           #
# https://github.com/chloezu                #
#-------------------------------------------#


"""
    TODOs

    - Find some way of cropping older images based on something not vague, such as resolution
    - Rewrite some of the functions to be less jank, and more resiliant to changes on google's side
"""

import sys
import requests
import os
import shutil
import subprocess


def get_pano_id() -> str:
    try:
        # pano ids seem to be 22 chars long, and always have 3D before it
        if len(sys.argv[1]) == 22:
            print(f"ID: {sys.argv[1]}")
            return sys.argv[1]

        # If link, sort for pano id
        pano_id = sys.argv[1].split("%")
        for i, value in enumerate(pano_id):
            if value == "26panoid":
                print(f"ID: {pano_id[i + 1][2:]}")
                return pano_id[i + 1][2:]
    except Exception:
        print("Error in get_pano_id()! Check your link!")
        sys.exit(1)


def get_date() -> str:  # TODO: This function may be buggy! Fix!
    # panoids are 22 chars long
    if len(sys.argv[1]) == 22:
        print("PanoID passed, defaulting date to null!")
        return str("")

    # Grab the date from the link, if applicable
    try:
        link = str(sys.argv[1])
        link = link.split('!2e0!5s', 1)[1]
        date = link.split('T000000!', 1)[0]
    except Exception:
        print("\nDate not found!")
        print("If you want the date in the image name, please see README.MD")
        print("If you wish to continue press any key, otherwise ctrl + c")
        input()
        print("Defaulting to null!\n")
        return str("")

    print(f"DATE: {date}")
    return date + "_"


def get_coords() -> str:  # TODO: This function may be buggy! Fix!
    # panoids are 22 chars long
    if len(sys.argv[1]) == 22:
        print("PanoID passed, defaulting coords to null!")
        return str("")

    # Grab the coords from the link, if applicable
    link = str(sys.argv[1])
    link = link.split('@', 1)[1]
    link = link.split(',3a', 1)[0]
    coords = link.replace(',', '_')

    print(f"COORDS: {coords}")
    return coords + "_"


def create_temp(id: str) -> str:
    working_dir = os.path.join(os.getcwd(), f'.tmp-{id}')
    os.makedirs(working_dir, exist_ok=True)
    print(f"DIR: {working_dir}")
    return working_dir


def clear_temp(working_dir: str) -> None:
    print("Cleaning temp files...")
    shutil.rmtree(working_dir)


# Should probably rewrite this to count up from 0, instead of down from 20
def get_dial_zoom(pano_id: str) -> int:
    image_zoom = 20
    while True:
        response = requests.get(f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile&panoid={pano_id}&x=0&y=0&zoom={image_zoom}&nbt=1")
        if response.status_code == 200:
            break
        image_zoom -= 1

    return image_zoom


# Names.txt is used to stitch the tiles together
# Only change if absolutely needed!
def write_names(filenames, path: str):
    with open(os.path.join(path, 'names.txt'), 'w') as file:
        file.write('\n'.join(filenames))


# Could be beneficial to grab the tile size from the image, incase google ever changes it
def create_pano_img(txt_path: str, filename: str, x: int, y: int):
    # Tiles are 512 x 512, needed for exiftool res
    width = (x + 1) * 512
    height = (y + 1) * 512

    print("Creating panoramic image...")
    subprocess.run(f"montage -adjoin @{txt_path} -tile {x + 1}x{y + 1} -geometry 512x512+0+0 -quality 100 {filename}.jpg", shell=True)

    if x == 6:  # Images this old need to be cropped due to overlap and blank space, aka, a little jank
        width, height = 3328, 1664
        subprocess.run(f"magick {filename}.jpg -crop {width}x{height}+0+0 {filename}.jpg",shell=True)

    print("Adding exif metadata...")
    subprocess.run(f"exiftool -overwrite_original -UsePanoramaViewer=True -ProjectionType=equirectangular "
                   f"-PoseHeadingDegrees=180.0 -CroppedAreaLeftPixels=0 -FullPanoWidthPixels={width} "
                   f"-CroppedAreaImageHeightPixels={height} -FullPanoHeightPixels={height} "
                   f"-CroppedAreaImageWidthPixels={width} -CroppedAreaTopPixels=0 -LargestValidInteriorRectTop=0 "
                   f"-LargestValidInteriorRectWidth={width} -LargestValidInteriorRectHeight={height} \""
                   f"{filename}.jpg\"", shell=True)


def download_tiles(pano_id: str, filepath: str) -> tuple[int, int]:
    final_zoom = get_dial_zoom(pano_id)
    x, y = 0, 0
    x_max, y_max = 2048, 2048
    filenames = []

    print("Beginning download...")

    while True:
        if x > x_max:
            x = 0
            y += 1

        image_link = f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile&panoid={pano_id}&x={x}&y={y}&zoom={final_zoom}&nbt=1"
        filename = f"_tmp_{pano_id}_x{x}_y{y}.jpg"

        with requests.get(image_link, stream=True) as req:
            if req.status_code == 400:
                if x_max == 2048:
                    x_max = x - 1  # Gets returned later, important
                elif y_max == 2048:
                    y_max = y - 1  # Also gets returned later
                    write_names(filenames, filepath)
                    print(f"X: {x_max + 1} | Y: {y_max + 1}")
                    return x_max, y_max  # If y_max is hit, we've reached the end of the image
            else:  # Downloads the tile
                current_file = os.path.join(filepath, filename)
                filenames.append(current_file)

                with open(current_file, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=8192):
                        f.write(chunk)

        x += 1  # Must be incr here, earlier causes issues!


def main() -> int:
    pano_id = get_pano_id()

    date = get_date()

    coords = get_coords()

    print(date + coords + pano_id)

    temp_dir = create_temp(pano_id)

    x_max, y_max = download_tiles(pano_id, temp_dir)

    create_pano_img(os.path.join(temp_dir, 'names.txt'), (date + coords + pano_id), x_max, y_max)
    clear_temp(temp_dir)

    print("Script finished!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
