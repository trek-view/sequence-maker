# Sequence Maker

## In one sentence

Command line Python script that 1) takes geotagged 360 images, 2) reads latitude, longitude and altitude, 3) automatically calculates connections between photos, and 4) embeds connections as JSON object in image metadata.

## Why we built this

We shoot 360 tours of the natural world (paths, rivers, bike trails...).

As we shoot photos in a timelapse, each photo in the timelapse has a relationship (e.g. photo 1 is connected to photo 2, photo 2 ...).

This information is not embedded into the images by the camera.

When uploading images to Google Street View and others, there is the option to explicitly define connection information at upload (vs. calculation on Google servers).

Sometimes we also shoot at a high frame rate (or get stopped on route). This means many photos get taken very close to each other, which we would otherwise have to discard manually.

To ensure the correct connections are made between photos we use Sequence Maker to define these connections from a series of timelapse photos. 

## How it works

1. You define the timelapse series of photos, desired photo spacing (by distance or capture time), and how they should be connected
2. IF distance selected, the script calculates the distance between photos
3. The script orders the photos in specified order (either capture time or distance)
4. The script discards images that don't match the specified spacing condition
5. The script calculates the distance, elevation change, time difference, and heading between remaining photos
6. The script writes a JSON object into the remaining photos `-xmp:Notes` tag with this information
 
## Requirements

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements

* Python version 3.6+
* [exiftool](https://exiftool.org/)

### Image Requirements

All images must be geotagged with the following values:

* `GPSLatitude`
* `GPSLongitude`
* `GPSAltitude`
- `GPSDateTime` OR (`GPSDateStamp` / `GPSTimeStamp`)

If a photo does not contain this information, you will be presented with a warning, and asked whether you wish continue (discard the photos missing this information from the process).

This software will work with most image formats. Whilst it is designed for 360 photos, it will work with a sequence of traditional flat (Cartesian) images too.

## Quick start guide

### Installation

The following Python packages need to be installed:
* [Pandas](https://pandas.pydata.org/docs/)
	`python -m pip install pandas`
	
[PyExifTool](https://pypi.org/project/PyExifTool/) is used as a package as well. This package is provided within this repo with the exiftool.py content being the content of a specific commit to address Windows related issues.


[exiftool](https://exiftool.org/) needs to be installed on the system.
If used on Windows, download the stand-alone .exe executable. Rename the .exe file to `exiftool.exe`. Put the .exe file in the same folder as the `azipi.py` file

The `.ExifTool_Config` ([.ExifTool_Config explanation](https://exiftool.org/faq.html#Q11)) needs be in the HOME directory (Mac, Linux) or in the same folder as the `azipi.py`file (Windows)

### Arguments

* -f: frame-rate: maximum frames per second (value between 0.05 and 5)

_A note on frame-rate spacing:  designed to discard photos when unnecessary high frame rate. the script will start on first photo and count to the nearest photo by value specified. All photos in between will be discarded. The script will then start from 0 and count to the next photo using the value specified. All photos in between will be discarded._

* -s: spatial-distance-min: minimum spacing between photos in meters (between 0.5 and 20) e.g. photos cannot be closer than this value.

_A note on spatial-distance-min: designed to discard photos when lots taken in same place. if the value you define is less than the distance between two photo values, the script will still make a connection (e.g min_spacing = 10m and actual disantce = 20m, photos will still be joined. The script will start on first photo and count to the nearest photo by value specified. All photos in between will be discarded. The script will then start from 0 and count to the next photo using the value specified. All photos in between will be discarded._

* -a: altitude-difference-min: minimum altitude difference between photos in meters.


_Note, if two or more of these arguments are used (frame-rate, spatial-distance-min, or altitude-difference-min arguments), the script will process in the order: 1) frame-rate, 2) spatial-distance-min, and 3) altitude-difference-min._

* -j: join mode:
	- time (ascending e.g. 00:01 - 00:10); OR
	- filename (ascending e.g A.jpg > Z.jpg)

	_A note on join modes: generally you should join by time unless you have a specific usecase. time will join the photo to the next photo using the photos `GPDateTime` value. Filename will join the photo to the next photo in ascending alphabetical order._

* -d: discard: discard images that lack GPS or time tags and continue

* e: exiftool-exec-path
	- path to ExifTool executable (recommended on Windows if [exiftool.exe](https://exiftool.org/) is not in working directory)

* input_directory: directory that contains a series of images

* output_directory: directory to store the newly tagged images


![Sequence maker joins](/sequence-maker-diagram.jpg)

### Format

```
python sequence-maker.py -[SPACING] [SPACING VALUE] -[JOIN MODE] -d -e [PATH TO EXIFTOOL EXECUTABLE] [INPUT PHOTO DIRECTORY] [OUTPUT PHOTO DIRECTORY]
```

### Examples

**Connect photos with a minimum interval of 1 seconds and minimum distance between photos of 3 meters in ascending time order (recommended)**

Mac, Linux:
```
python sequence-maker.py -f 1 -s 3 -j time -d time my_input_photos/ my_output_photos/
````
Windows:
```
"C:\Program Files (x86)\Python37\python.exe" "C:\PATH TO Python file\sequence-maker.py" -f 1 -s 3 -j time -d -e "C:\PATH TO exiftool\exiftool.exe" "C:\PATH TO INPUT FOLDER\" "C:\PATH TO OUTPUT FOLDER\"
```

**Connect photos within 10m of each other in ascending time order (recommended)**

### Output

Sequence maker will generate new photo files with JSON objects with destination connections printed under the [EXIF] `ImageDescription` tag:

```
{
	connections: {
		[FILENAME_1]: {
			distance_mtrs: # horizontal distance (haversine) to destination file
			elevation_mtrs: # vertical distance to destination file
			heading_deg: # between 0 and 360
			time_sec: # time in seconds before destination file captured (can be negative, if source photo taken after destination photo -- for example, when moving backwards)
		},
		[FILENAME_n]: {
			distance_mtrs:
			elevation_mtrs:
			heading_deg:
			time_sec: 
	}
	create_date: 2020-05-30:00:00:00
	software: sequence-maker
}

```
You will get a new photo file with appended meta data.

The new files will follow the naming convention: `[ORIGINAL FILENAME] _ calculated . [ORIGINAL FILE EXTENSION]`


You can view the the value of tags assigned:

```
exiftool -G -a  exiftool PHOTO_FILE > PHOTO_FILE_metadata.txt
```

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Sequence Maker is licensed under a [GNU AGPLv3 License](https://github.com/trek-view/sequence-maker/blob/master/LICENSE.txt).