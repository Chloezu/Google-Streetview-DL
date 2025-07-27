#!/bin/python3

#-------------------------------------------#
#                  Credits                  #
#-------------------------------------------#
# fdd4s for the idea, code structure        #
#               and php base                #
# https://github.com/fdd4s/streetview-dl    #
#-------------------------------------------#
# Seloris for making my code readable       #
# https://github.com/allocazione            #
#-------------------------------------------#
# Chloezu [me], functional but crappy       #
# python rewrite of fdd4s' script           #
# https://github.com/chloezu                #
#-------------------------------------------#


"""
    TODOs
    - Rewrite some of the functions to be less jank, and more resiliant to changes on google's side
"""

import sys
import requests
import os
import shutil
import subprocess
import re


def get_pano_id() -> str:
    """
    Extracts the pano ID from the command-line argument
    Returns the ID if passed directly, or extracts it from a URL
    """
    try:
        arg = str(sys.argv[1])
        # If the argument is a direct panoid (22 chars)
        if len(arg) == 22:
            print(f"ID: {arg}")
            return arg
        # Otherwise, try to extract from a URL
        parts = arg.split("%")
        for i, value in enumerate(parts):
            if value == "26panoid":
                panoid = parts[i + 1][2:]
                print(f"ID: {panoid}")
                return panoid
    except Exception:
        print("Error in get_pano_id()! Check your link!")
        sys.exit(1)


def get_date() -> str:
    """
    Extracts the date (YYYYMMDD) from a Google Street View URL if present
    Returns an empty string if not found or if a panoid is passed directly
    """

    arg = str(sys.argv[1])
    if len(arg) == 22:
        print("PanoID passed, defaulting date to null!")
        return ""
    # Use regex to find an 8-digit date before 'T000000!'
    match = re.search(r'([0-9]{8})T000000!', arg)
    if match:
        date = match.group(1)
        print(f"DATE: {date}")
        return date + "_"
    print("Date not found! Defaulting to null!")
    return ""


def get_coords() -> str:
    """
    Extracts coordinates from a Google Street View URL if present
    Returns an empty string if not found or if a panoid is passed directly
    """

    arg = str(sys.argv[1])
    if len(arg) == 22:
        print("PanoID passed, defaulting coords to null!")
        return ""
    # Use regex to find coordinates after '@'
    match = re.search(r'@([\d.\-]+,[\d.\-]+)', arg)
    if match:
        coords = match.group(1).replace(',', '_')
        print(f"COORDS: {coords}")
        return coords + "_"
    print("Coords not found! Defaulting to null!")
    return ""


def create_temp(panoid: str) -> str:
    """
    Creates a temporary working directory for the given panoid
    """

    working_dir = os.path.join(os.getcwd(), f'.tmp-{panoid}')
    os.makedirs(working_dir, exist_ok=True)
    print(f"DIR: {working_dir}")
    return working_dir


def clear_temp(working_dir: str) -> None:
    """
    Removes the temporary working directory and its contents
    """

    print("Cleaning temp files...")
    shutil.rmtree(working_dir)


def get_dial_zoom(pano_id: str) -> int:
    """
    Determines the highest available zoom level for the panorama
    """

    image_zoom = 20
    while image_zoom >= 0:
        response = requests.get(
            f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile&panoid={pano_id}&x=0&y=0&zoom={image_zoom}&nbt=1"
        )
        if response.status_code == 200:
            break
        image_zoom -= 1
    return image_zoom


def write_names(filenames, path: str):
    """
    Writes the list of tile filenames to names.txt for montage
    """

    with open(os.path.join(path, 'names.txt'), 'w') as file:
        file.write('\n'.join(filenames))


def create_pano_img(txt_path: str, filename: str, x_tiles: int, y_tiles: int):
    """
    Stitches tiles into a panoramic image and crops if needed based on resolution
    Adds EXIF metadata for panorama viewers
    """

    tile_size = 512
    width = (x_tiles + 1) * tile_size
    height = (y_tiles + 1) * tile_size

    print("Creating panoramic image...")
    subprocess.run(
        f"montage -adjoin @{txt_path} -tile {x_tiles + 1}x{y_tiles + 1} -geometry {tile_size}x{tile_size}+0+0 -quality 100 {filename}.jpg",
        shell=True
    )

    # Robust cropping for old images based on actual resolution
    cropped = False
    try:
        from PIL import Image
        img = Image.open(f"{filename}.jpg")
        actual_width, actual_height = img.size
        # If the image is larger than 3328x1664, crop to that size (old format)
        if actual_width > 3328 and actual_height > 1664:
            print("Cropping old format image to 3328x1664...")
            img = img.crop((0, 0, 3328, 1664))
            img.save(f"{filename}.jpg")
            width, height = 3328, 1664
            cropped = True
    except ImportError:
        # Fallback to ImageMagick crop if PIL(Pillow) is not available
        if x_tiles == 6:
            width, height = 3328, 1664
            subprocess.run(f"magick {filename}.jpg -crop {width}x{height}+0+0 {filename}.jpg", shell=True)
            cropped = True

    if cropped:
        print(f"Cropped image to {width}x{height}.")

    print("Adding exif metadata...")
    subprocess.run(
        f"exiftool -overwrite_original -UsePanoramaViewer=True -ProjectionType=equirectangular "
        f"-PoseHeadingDegrees=180.0 -CroppedAreaLeftPixels=0 -FullPanoWidthPixels={width} "
        f"-CroppedAreaImageHeightPixels={height} -FullPanoHeightPixels={height} "
        f"-CroppedAreaImageWidthPixels={width} -CroppedAreaTopPixels=0 -LargestValidInteriorRectTop=0 "
        f"-LargestValidInteriorRectWidth={width} -LargestValidInteriorRectHeight={height} "
        f'"{filename}.jpg"',
        shell=True
    )


def download_tiles(pano_id: str, filepath: str) -> tuple[int, int]:
    """
    Downloads all tiles for the panorama and returns the max x and y tile indices
    """

    final_zoom = get_dial_zoom(pano_id)
    x, y = 0, 0
    x_max, y_max = 2048, 2048
    filenames = []

    print("Beginning download...")

    while True:
        if x > x_max:
            x = 0
            y += 1

        image_link = (
            f"https://streetviewpixels-pa.googleapis.com/v1/tile?cb_client=maps_sv.tactile"
            f"&panoid={pano_id}&x={x}&y={y}&zoom={final_zoom}&nbt=1"
        )
        filename = f"_tmp_{pano_id}_x{x}_y{y}.jpg"

        with requests.get(image_link, stream=True) as req:
            if req.status_code == 400:
                if x_max == 2048:
                    x_max = x - 1
                elif y_max == 2048:
                    y_max = y - 1
                    write_names(filenames, filepath)
                    print(f"X: {x_max + 1} | Y: {y_max + 1}")
                    return x_max, y_max
            else:
                current_file = os.path.join(filepath, filename)
                filenames.append(current_file)
                with open(current_file, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=8192):
                        f.write(chunk)
        x += 1


def main() -> int:
    # 1. Parse input and extract identifiers
    pano_id = get_pano_id()
    date_prefix = get_date()
    coords_prefix = get_coords()
    output_prefix = f"{date_prefix}{coords_prefix}{pano_id}"
    print(f"Output prefix: {output_prefix}")

    # 2. Prepare temporary working directory
    temp_dir = create_temp(pano_id)

    # 3. Download all tiles for the panorama
    x_max, y_max = download_tiles(pano_id, temp_dir)

    # 4. Stitch tiles and add metadata
    names_txt_path = os.path.join(temp_dir, 'names.txt')
    create_pano_img(names_txt_path, output_prefix, x_max, y_max)

    # 5. Clean up temporary files
    clear_temp(temp_dir)

    print("Script finished!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
