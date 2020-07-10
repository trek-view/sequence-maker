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

### Overview

1. You define the timelapse series of photos, desired photo spacing (by distance or time), and how they should be connected
2. IF distance selected, the script calculates the distance between photos
3. The script orders the photos in specified order (time or distance)
4. The script discards images that don't match the specified spacing condition
5. The script assigns each photo a UUID 
6. The script calculates the distance, elevation change, time difference, and heading between remaining photos
7. The script uses exiftool to write a JSON object into the remaining photos `-exif:ImageDescription` tag with this information
 
### The details

A sequence is a series of images (e.g. a series of 360 images on a hiking route). A sequence is defined by the images supplied by user to the script (directory).

The order of joins (what photo is connected to the next) is defined by the user at script runtime (either timegps, timecapture, or filename).

![Sequence maker joins](/readme-images/sequence-maker-diagram.jpg)

For geotagged photos taken in a timelapse, it is possible to provide a fairly accurate estimate of the azimuth and pitch (see: limitations) because timelapses are typically shot in ascending time order (00:00:00 > 00:00:05 > 00:00:10) at set intervals (e.g. one photo every 5 seconds). 

* elevation change to destination (`elevation_mtrs`): reported as `GPSAltitude`, can be calculated as "destination photo altitude - source photo altitude"
* distance to destination (`distance_mtrs`): using position of two photos (`GPSLatitude` to `GPSLongitude`) can calculate distance using the [Haversine formula](https://en.wikipedia.org/wiki/Haversine_formula)
* time difference to destination (`time_sec`): using either `GPSDateTime` or `originalDateTime`, can be calculated as  as "destination photo time - source photo time"
* speed to destination (`speed_kmh`): using `distance_mtrs` and `time_sec` it is possible to calculate speed between two photos (speed = `distance_mtrs` / `time_sec`)
* azimuth to destination (`heading_deg`) (estimate): calculated using the vertical angle between the `GPSAltitude` value of source and destination photo.
* pitch to destination (`pitch_deg`) (estimate): calculated using the horizontal angle between the source photo (`GPSLatitude`/`GPSLongitude`) and the destination photo (`GPSLatitude`/`GPSLongitude`).
* adjusted heading to destination (`adj_heading_deg`): reported in degrees between 0 and 359.99 degrees. Only calculated for previous photo connection. Calculated using next photo `heading_deg` - previous `heading_deg`. Calculation can return negative value, in which case it is converted to positive number.

Once all these have been calculated, it is possible to calculate the following values for sequence level information.

* sequence distance_km
* sequence earliest_time
* sequence latest_time
* sequence duration_sec 
* sequence average_speed

The output calculations allow us to write the following JSON object information into the ImageDescription field.

```
{
	"sequence" : {
		"id": # UUID of sequence,
		"distance_km": # total distance using all positive distance_mtrs connection values
		"earliest_time": # earliest time GPSDateTime (if connection method gps / filename) or originalDateTime (if connection originalDateTime) value for photo in sequence,
		"latest_time": # latest time GPSDateTime (if connection method gps / filename) or originalDateTime (if connection originalDateTime) value for photo in sequence,
		"duration_sec: # sequence_latest_time - sequence_earliest_time,
		"average_speed_kmh": # sequence_distance_km / sequence_duration_sec
		"uploader_sequence_name": # not currently used
		"uploader_sequence_description": # not currently used
		"uploader_transport_type": # not currently used
	}
	"photo" : {
		"id": # generated UUID of this photo,
		"original_GPSDateTime": # GPSDateTime value,
		"original_originalDateTime": # originalDateTime value,
		"cli_connection_method": # GPSDateTime, originalDateTime, or filename depending on connection mode selected,
		"cli_frame_rate_set": # value set for -f,
		"cli_altitude_min_set": # value set for -a,
		"cli_distance_min_set": # value set for -s,
		"original_filename": # filename of photo before modifications,
		"original_altitude": # GPSAltitude value,
		"original_latitude": # GPSLatitude value,
		"original_longitude": # GPSLongitude value,
		"orignal_gps_direction_ref": # GPSImgDirectionRef value, else "",
		"orignal_gps_speed": # GPSSpeed value, else "",
		"original_heading": # XMP PoseHeadingDegrees` else EXIF `GPSImgDirection`, else "",
		"original_pitch": # XMP PosePitchDegrees else EXIF GPSPitch, else "",
		"original_roll": # XMP PosePoseRollDegrees else EXIF GPSRoll, else "",
		"original_camera_make": Make value,
		"original_camera_model": Model value,
		"software_version": 1.0 # shows version of sequence maker used from version txt,
		"uploader_photo_from_video": # not currently used,
		"uploader_nadir_added": # not currently used,
		"uploader_blur_added": # not currently used,
		"uploader_gps_track_added": # not currently used,
		"uploader_gps_modified": # not currently used,
		"uploader_tags": [] # not currently used
		"connections": {
			"[CONNECTION_1_PHOTO_UUID (NEXT PHOTO)]": {
				"distance_mtrs": # reported in meters (can be negative, if source photo taken after destination photo),
				"elevation_mtrs": # reported in meters (can be negative if destination photo is lower)
				"time_sec": # reported in seconds (can be negative, if source photo taken after destination photo),
				"speed_kmh": # reported in kilometers per hour (can be negative, if source photo taken after destination photo),
				"heading_deg": # reported in degrees between 0 and 359.99 degrees,
				"adj_heading_deg": # reported in degrees between 0 and 359.99 degrees. reported for previous photo connection only,
				"pitch_deg": # reported in degrees between -90 to 90 degrees
		},
			"[CONNECTION_2_PHOTO_UUID (PREVIOUS PHOTO)]": {
			}
		}

} 
```

First and last photos in seqence always have 1 connection (either forward and back). All other photo connections will have 2 connections (both forward and back).

```
		"connections": {
			[51993d0d-af02-11ea-922c-cd0ce84081fa]: {
				"distance_mtrs": 12.666786535950974,
				"elevation_mtrs": 0.43100000000004,
				"time_sec": 10,
				"speed_kmh": 6.666786535950974,
				"heading_deg": 178.76974201469432,
				"adj_heading_deg": ,
				"pitch_deg": 0.03402599378909342
				},
			[748495d0d-af03-19fa-048a-cf8ce74089ui]: {
				"distance_mtrs": -22.039488888888888,
				"elevation_mtrs": -0.73700000000002,
				"time_sec": -10,
				"speed_kmh": -6.546786535950975,
				"heading_deg": 350.88884201469438,
				"adj_heading_deg": "172.1191",
				"pitch_deg": -0.05502599378909355
				}
			}
```

The script will also output a single JSON document (SEQUENCE_ID.json) containing sequence information, and details of all photos in sequence.

### Limitations / Considerations

**Estimations**

Photos in our (Trek View) tours are generally less than 3m apart and our Trek Pack cameras are always facing forward / backwards in the same direction (in a fixed position). Azimuth / Pitch Calculator therefore makes the assumption that the camera is facing in the direction of the next photo (as defined in CLI arguments).

Note, this will not always be correct, for example, if camera turns 90 degrees between start and destination photo (e.g turning a corner). In such cases, using this software could result in photos facing the wrong direction and causing visual issues (e.g. facing a brick wall if turning 90 degrees around a city block). However, for our outdoor work this is rarely a problem and is considered acceptable.

If you're shooting at a low frame rate, sharply changing direction, or holding your camera at different angles (e.g holding in your hand), this script will not be a good fit for you.

**Discarded images**

This script allows you to discard images that don't match a certain criteria (for example, you want to space them a minimum of 10 meters apart) and will lead to a larger level of inaccuracy for estimations.

In cases where more images are discarded the source and destination photo used for calculations might therefore be very far apart, and thus less likely for the source photo to be facing the destination photo.

**Missing GPS**

This script assumes all images are correctly geotagged with GPS information.

If an image is not geotagged for some reason, you can still use the script but it will lead to a larger level of inaccuracy for estimations. This is because images with no GPS information are discarded. In cases where there has been loss of GPS information for a long period of time, the source and destination photo used for calculations might therefore be very far apart, and thus less likely for the source photo to be facing the destination photo.

## Requirements

### OS Requirements

Works on Windows, Linux and MacOS.

### Software Requirements / Installation

The following software / Python packages need to be installed:

* Python version 3.6+
* [Pandas](https://pandas.pydata.org/docs/): `python -m pip install pandas`
* [PyExifTool](https://pypi.org/project/PyExifTool/): is used as a package as well. This package is provided within this repo with the `exiftool.py` content being the content of a specific commit to address Windows related issues.
* [exiftool](https://exiftool.org/) needs to be installed on the system. If used on Windows, download the stand-alone .exe executable. Rename the .exe file to `exiftool.exe`. Put the .exe file in the same folder as the `azipi.py` file

The `.ExifTool_Config` ([.ExifTool_Config explanation](https://exiftool.org/faq.html#Q11)) needs be in the HOME directory (Mac, Linux) or in the same folder as the `azipi.py`file (Windows)

### Image Requirements

All images must be geotagged with the following values:

* `GPSLatitude`
* `GPSLongitude`
* `GPSAltitude`
* `GPSDateTime` OR (`GPSDateStamp` AND `GPSTimeStamp`) OR `originalDateTime`

If a photo does not contain this information, you will be presented with a warning, and asked whether you wish continue (discard the photos missing this information from the process).

This software will work with most image formats. Whilst it is designed for 360 photos, it will work with a sequence of traditional flat (Cartesian) images too.

## Quick start guide

### Command Line Arguments

* -f: frame rate (optional: default is keep all images). Maximum frames per second. Enter value between 0.05 and 5 (frames per second).

_A note on frame rate spacing. `-f` is designed to discard photos when unnecessary high frame rate of images exists. The script will start on first photo in the specified order and count to the nearest photo using the frame rate value specified. All photos in between will be discarded. The script will then start from 0 and count to the next photo using the frame rate value specified, and so on._

* -s: spatial distance minimum in meters (optional: default is keep all images). The minimum spacing between photos in meters. Put another way, photos cannot be closer than this value. Enter value between 0.5 and 20 (meters).

_A note on spatial distance minimum. `-s` is designed to discard photos when lots taken in same place. The script will start on first photo and count to the nearest photo using the distance value specified. All photos in between will be discarded. The script will then start from 0 and count to the next photo using the value distance specified, and do on._

* -a: altitude difference minimum in meters (optional: default is keep all images). The minimum altitude difference between photos in meters. Enter value between 0.5 and 20 (meters).

_A note on spatial distance minimum. `-a`. is really designed for skydiving to discard photos when lots taken in same vertical space. Works in same way as `-s` but for vertical distance between photos._

**Using `-f`, `-s` and `-a` together**

If two or more of these arguments are used (`-f`, `-s` or `-a`) the script will process in the order: 1) frame rate `-f`, 2) spatial distance minimum `-s`, and 3) altitude difference minimum `-a`.

* -c: connection mode (optional: default is timegps):
	- timegps (`GPSDateTime` of image, ascending e.g. 00:01 - 00:10); OR
	- timecapture (`CaptureTime` of image, ascending e.g. 00:01 - 00:10)
	- filename (ascending e.g A.jpg > Z.jpg)

_A note on connection modes. Generally you should connect by time unless you have a specific use-case. Filename will connect the photo to the next photo in ascending alphabetical order. We recommend using `timegps` ([EXIF] `GPSDateTime`) not `timecapture` ([EXIF] `originalDateTime`) unless you are absolutely sure `originalDateTime` is correct. Many 360 stitching tools rewrite `originalDateTime` as datetime of stitching process not the datetime the image was actually captured. This can cause issues when sorting by time (e.g. images might not be stitched in capture order). Therefore, `GPSDateTime` is more likely to represent the true time of capture._

* d: discard: discard images that lack GPS or time tags and continue (required: if no GPS data in image)
* e: exiftool-exec-path (optional)
	- path to ExifTool executable (recommended on Windows if [exiftool.exe](https://exiftool.org/) is not in working directory)
* input_directory: directory that contains a series of images
* output_directory: directory to store the newly tagged images

### Format

```
python sequence-maker.py -[SPACING] [SPACING VALUE] -[CONNECT MODE] -d -e [PATH TO EXIFTOOL EXECUTABLE] [INPUT PHOTO DIRECTORY] [OUTPUT PHOTO DIRECTORY]
```

### Examples

**Connect photos with a minimum interval of 1 seconds and minimum distance between photos of 3 meters in ascending time order discarding images that lack gps (recommended)**

_Mac/Linux_

```
python sequence-maker.py -f 1 -s 3 -c timegps -d INPUT_DIRECTORY OUTPUT_DIRECTORY
````

_Windows_

```
python sequence-maker.py -f 1 -s 3 -c timegps -d "INPUT_DIRECTORY" "OUTPUT_DIRECTORY"
```

### Output

If successful an output similar to that shown below will be shown:

```
8 file(s) have been found in input directory
Fetching metadata from all images....

Checking metadata tags of all images...
1 images dropped. "DISCARD" is True.

Calculating differences of time, distance and altitude between images...
Filtering images according to input parameters...
0 images discarded due to time spacing intervals
0 images discarded due to distance spacing intervals
0 images discarded due to altitude spacing intervals


Final amount of images to process: 7


Calculating final differences of time, distance and altitude between qualified images...
Calculating heading between qualified images....
Setting related data of connected qualified images...

Generating JSON object...
Writing metadata to EXIF::ImageDescription of qualified images...

Cleaning up old and new files...
Output files saved to C:\Users\david\azimuth-pitch-calculator-master\OUTPUT

Metadata successfully added to images.

```

You will get a new photo file with appended metadata.

The new files will follow the naming convention: `[ORIGINAL FILENAME] _ calculated . [ORIGINAL FILE EXTENSION]`

For example, `INPUT/MULTISHOT_9698_000000.jpg` >> `OUTPUT/MULTISHOT_9698_000000_calculated.jpg`

## FAQ

**How can I check the metadata in the image?**

You can use exiftool (which will already be installed) to check the metadata.

This skeleton command will output all the metadata in the specified image:

```
exiftool -G -s -b -c -a -T [PATH OF IMAGE TO CHECK] > OUTPUT.json
```

It will give a complete JSON document. Here's a snippet of the output:

```
  "EXIF:ImageDescription": {
    "id": 270,
    "table": "Exif::Main",
    "val": ""id\": \"51993d0c-af02-11ea-a62e-cd0ce84081fa\", \"create_date\": \"2020-06-15:13:18:28\", \"software\": \"sequence-maker\", {\"connections\": {\"51993d0d-af02-11ea-922c-cd0ce84081fa\": {\"distance_mtrs\": 12.666786535950974, \"elevation_mtrs\": 0.43100000000004, \"heading_deg\": 178.76974201469432, \"pitch_deg\": 0.03402599378909342, \"time_sec\": 10, \"speed_kmh\": 6.666786535950974,}}"
  },
```

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Sequence Maker is licensed under a [GNU AGPLv3 License](/LICENSE.txt).