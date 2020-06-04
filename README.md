# Sequence Maker

## In one sentence

Command line Python script that 1) takes geotagged 360 images, 2) reads latitude, longitude and altitude, 3) automatically calculates connections between photos, and 4) embeds connections as json object in image metadat

## Why we built this

We shoot 360 tours of the natural world (paths, rivers, bike trails...).

As we shoot photos in a timelapse, each photo in the timelapse has a relationship (e.g. photo 1 is connected to photo 2, photo 2 ...).

This information is not embedded into the images by the camera.

When uploading images to Google Street View and others, there is the option to explicityly define connection information at upload (vs. calcualation on Google servers).

To ensure the correct connections are made between photos we use Sequence Maker to define these connections from a series of timelapse photos. 

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
* `GPSDateTime`

If a photo does not contain this infortmation, you will be presented with a warning, and asked wether you wish continue (discard the photos missing this inforamtion from the process).

This software will work with most image formats. Whilst it is designed for 360 photos, it will work with a sequence of traditional flat (Cartesian) images too.

## Support 

We offer community support for all our software on our Campfire forum. [Ask a question or make a suggestion here](https://campfire.trekview.org/c/support/8).

## License

Sequence Maker is licensed under a [GNU AGPLv3 License](https://github.com/trek-view/sequence-maker/blob/master/LICENSE.txt).