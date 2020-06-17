# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Author: hq@trekview.org
# Created: 2020-06-04
# Copyright: Trek View
# Licence: GNU AGPLv3
# -------------------------------------------------------------------------------


import math
import os
from pathlib import Path
import datetime
import json
import sys
import argparse
import ntpath
import time
import uuid

import pandas as pd
from exiftool_custom import exiftool


def calculate_initial_compass_bearing(pointA, pointB):
    '''
    Calculate the compass bearing (azimuth) between two points 
    on the earth (specified in decimal degrees)
    https://github.com/trek-view/tourer/blob/latest/utils.py#L114
    '''
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError('Only tuples are supported as arguments')

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def haversine(lon1, lat1, lon2, lat2):
    '''
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    https://github.com/trek-view/tourer/blob/latest/utils.py#L134
    '''
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371

    distance = (c * r) * 1000

    return distance


def get_files(path, isdir):
    '''
    Return a list of files, or directories.
    '''
    list_of_files = []

    for item in os.listdir(path):
        itemPath = os.path.abspath(os.path.join(path,item))
        
        if isdir:
            if os.path.isdir(itemPath):
                list_of_files.append(itemPath)
        else:
            if os.path.isfile(itemPath):
                list_of_files.append(itemPath)

    return list_of_files


def filter_metadata(dict_metadata, key, discard):
    '''
    For a given set of metadata for an image, return every key-value
    taking into account whether to discard it or not.
    '''
    if discard == True:
        try:
            return dict_metadata[key]
        except KeyError:
            #discard is True -> Set the value of the key to NaN, this picture will be thrown away
            return float('NaN')
    else:
        #discard is False -> throw a Keyerror and stop the program when certain metadata is not available
        return dict_metadata[key]

    
def parse_metadata(dfrow, keys, discard):
    '''
    Main function using filter_metadata() to process each key in a metadata object
    '''
    dict_metadata = dfrow['METADATA']
    values = []
    for key in keys:
        try:
            values.append(filter_metadata(dict_metadata, key, discard))
        except KeyError:
            print('\n\nAn image was encountered that did not have the required metadata.')
            print('Image: {0}'.format(dfrow['IMAGE_NAME']))
            print('Missing metadata key: {0}\n\n'.format(key.split(':')[-1]))
            print('Consider using the "-d" option to discard images missing required metadata keys')
            input('Press any key to quit')
            quit()
    return values


def generic_connection(df_images, connection_type, minimum):
    '''
    A function to calculate the difference and links of a certain difference type.
    Differences must be linear.
    '''
    df_images['CUM_{0}'.format(connection_type)] = float(0)

    for index, row in df_images.iterrows():
        if index == 0:
            df_images.iat[index, df_images.columns.get_loc('CUM_{0}'.format(connection_type))] = 0
        else:
            df_images.iat[index, df_images.columns.get_loc('CUM_{0}'.format(connection_type))] = df_images['CUM_{0}'.format(connection_type)].loc[index-1] + df_images[connection_type].loc[index]
        
            if df_images.iat[index, df_images.columns.get_loc('CUM_{0}'.format(connection_type))] >= minimum:
                df_images.iat[index, df_images.columns.get_loc('CUM_{0}'.format(connection_type))] = 0          

    #Only keep rows where cumdeltatime = 0 -> difference with previous picture bigger than minimum.
    #Actual cumulated values are recalculated later
    df_images = df_images[df_images['CUM_{0}'.format(connection_type)] == 0]
    df_images.reset_index(inplace = True, drop=True)

    return df_images


def calculate_to_next(df_images, connection_type):
    #3 required variables:
    # 1) time diff to next: DELTA_TIME
    # 2) distance to next: DISTANCE
    # 3) altitude diff to next: DELTA_ALT

    # 1)
    if connection_type == 'DELTA_TIME':
        df_images['GPS_DATETIME_NEXT'] = df_images['GPS_DATETIME'].shift(-1)
        df_images['DELTA_TIME'] = df_images['GPS_DATETIME_NEXT'] - df_images['GPS_DATETIME']
        df_images.iat[-1, df_images.columns.get_loc('DELTA_TIME')] = df_images.iat[-2, df_images.columns.get_loc('DELTA_TIME')] 
        df_images['DELTA_TIME'] = df_images.apply(lambda x: datetime.timedelta(seconds = x['DELTA_TIME'].seconds),axis=1)
        df_images['DELTA_TIME'] = df_images.apply(lambda x: x['DELTA_TIME'].seconds,axis=1)

    # 2) 
    elif connection_type == 'DISTANCE':
        df_images['LATITUDE_NEXT']     = df_images['LATITUDE'].shift(-1)
        df_images['LONGITUDE_NEXT']    = df_images['LONGITUDE'].shift(-1)
        df_images['ALTITUDE_NEXT']     = df_images['ALTITUDE'].shift(-1)
        df_images['DISTANCE'] = df_images.apply(lambda x: haversine(x['LONGITUDE'], x['LATITUDE'], x['LONGITUDE_NEXT'], x['LATITUDE_NEXT']),axis=1)
        df_images.iat[-1, df_images.columns.get_loc('DISTANCE')] = df_images.iat[-2, df_images.columns.get_loc('DISTANCE')]

    # 3)
    elif connection_type == 'DELTA_ALT':
        df_images['DELTA_ALT'] = df_images['ALTITUDE_NEXT'] - df_images['ALTITUDE']
        df_images.iat[-1, df_images.columns.get_loc('DELTA_ALT')] = df_images.iat[-2, df_images.columns.get_loc('DELTA_ALT')]

    return df_images

def clean_up_new_files(OUTPUT_PHOTO_DIRECTORY, list_of_files):
    '''
    As Exiftool creates a copy of the original image when processing,
    the new files are copied to the output directory,
    original files are renamed to original filename.
    '''

    print('Cleaning up old and new files...')
    if not os.path.isdir(os.path.abspath(OUTPUT_PHOTO_DIRECTORY)):
        os.mkdir(os.path.abspath(OUTPUT_PHOTO_DIRECTORY))

    for image in list_of_files:
        image_head, image_name = ntpath.split(image)
        try:
            os.rename(image, os.path.join(os.path.abspath(OUTPUT_PHOTO_DIRECTORY), '{0}_calculated.{1}'.format(image_name.split('.')[0], image.split('.')[-1])))
            os.rename(os.path.join(os.path.abspath(image_head), '{0}_original'.format(image_name)), image)
        except PermissionError:
            print("Image {0} is still in use by Exiftool's process or being moved'. Waiting before moving it...".format(image_name))
            time.sleep(3)
            os.rename(image, os.path.join(os.path.abspath(OUTPUT_PHOTO_DIRECTORY), '{0}_calculated.{1}'.format(image_name.split('.')[0], image.split('.')[-1])))
            os.rename(os.path.join(os.path.abspath(image_head), '{0}_original'.format(image_name)), image)

    print('Output files saved to {0}'.format(os.path.abspath(OUTPUT_PHOTO_DIRECTORY)))


def handle_frame_rate(frame_rate):
    '''
    Helper function to process frame rates and invalid values
    '''
    MAX_FRAME_RATE        = float(frame_rate)
    try:
        MIN_TIME_INTERVAL     = 1/MAX_FRAME_RATE
        return MAX_FRAME_RATE, MIN_TIME_INTERVAL
    except Exception:
        print("""Frame rate was set to 0 or to a string. This is not a correct value.
        Either use a non-zero numeric value or do not include the frame rate input parameter (default set to frame rate = 1 000 000).
        For example: 1000
        For example: 0.1""")

        MAX_FRAME_RATE_raw = input('Please type your new frame rate.\nPress enter to skip frame rate filtering: ')
        if MAX_FRAME_RATE_raw == '':
            MAX_FRAME_RATE = 1000000
            MIN_TIME_INTERVAL = 1/MAX_FRAME_RATE
            return MAX_FRAME_RATE, MIN_TIME_INTERVAL
        else:
            try: 
                float(MAX_FRAME_RATE_raw)
            except ValueError:
                input('Invalid frame rate. Press any key to quit.')
                quit()

            MIN_TIME_INTERVAL = 1/float(MAX_FRAME_RATE_raw) 

            return MAX_FRAME_RATE, MIN_TIME_INTERVAL


def make_sequence(args):
    '''
    You define the timelapse series of photos, desired photo spacing (by distance or capture time), and how they should be connected
    IF distance selected, the script calculates the distance between photos
    The script orders the photos in specified order (either capture time or distance)
    The script discards images that don't match the specified spacing condition
    The script calculates the distance, elevation change, time difference, and heading between remaining photos
    The script writes a JSON object into the remaining photos -Exif:ImageDescription tag with this information
    '''
    
    #Process import parameters
    print('\nInitializing input parameters...\n')

    # 'GPS_DATETIME' for sorting on 'time' or 'IMAGE_NAME' for sorting on 'filename'
    CONNECTION_TYPE       = 'GPS_DATETIME' if args.join_mode in ['time', 'Time', 't', 'T'] else 'IMAGE_NAME' 
    DISCARD               = True if args.discard == True else False

    MAX_FRAME_RATE, MIN_TIME_INTERVAL = handle_frame_rate(args.frame_rate)

    MIN_DISTANCE_INTERVAL = float(args.spatial_distance_min)
    MIN_ALTITUDE_INTERVAL = float(args.alt_diff_min)

    TIME_FILTERING        = True if MAX_FRAME_RATE < 1000000 else False
    DISTANCE_FITLERING    = True if MIN_DISTANCE_INTERVAL > 0 else False
    ALTITUDE_FITLERING    = True if MIN_ALTITUDE_INTERVAL > 0 else False

    PATH                   = Path(__file__)
    INPUT_PHOTO_DIRECTORY  = os.path.abspath(args.input_directory)
    OUTPUT_PHOTO_DIRECTORY = os.path.abspath(args.output_directory)

    if not os.path.isdir(os.path.abspath(INPUT_PHOTO_DIRECTORY)):
        if os.path.isdir(os.path.join(PATH.parent.resolve(), INPUT_PHOTO_DIRECTORY)):
            INPUT_PHOTO_DIRECTORY = os.path.join(PATH.parent.resolve(), INPUT_PHOTO_DIRECTORY)
            if not os.path.isdir(os.path.abspath(OUTPUT_PHOTO_DIRECTORY)):
                OUTPUT_PHOTO_DIRECTORY = os.path.join(PATH.parent.resolve(), OUTPUT_PHOTO_DIRECTORY)
        else:
            input('No valid input folder is given!\nInput folder {0} or {1} does not exist!'.format(os.path.abspath(INPUT_PHOTO_DIRECTORY), \
                os.path.abspath(os.path.join(PATH.parent.resolve(), INPUT_PHOTO_DIRECTORY))))
            input('Press any key to continue')
            quit()

    print('The following input folder will be used:\n{0}'.format(INPUT_PHOTO_DIRECTORY))
    print('The following output folder will be used:\n{0}'.format(OUTPUT_PHOTO_DIRECTORY))

    #Often the exiftool.exe will not be in Windows's PATH
    if args.executable_path == 'No path specified':
        if 'win' in sys.platform and not 'darwin' in sys.platform:
            if os.path.isfile(os.path.join(PATH.parent.resolve(), 'exiftool.exe')):
                exiftool.executable = os.path.join(PATH.parent.resolve(), 'exiftool.exe')
            else:
                input("""Executing this script on Windows requires either the "-e" option
                    or store the exiftool.exe file in the working directory.\n\nPress any key to quit...""")
                quit()
        else:
            pass #exiftool.executable  = 'exiftool', which if in OS PATH will be OK for mac and linux

    else:
        exiftool.executable = args.executable_path

    #Get files in directory
    list_of_files = get_files(INPUT_PHOTO_DIRECTORY, False)
    print('{0} file(s) have been found in input directory'.format(len(list_of_files)))

    #Get metadata of each file in list_of_images
    print('Fetching metadata from all images....\n')
    with exiftool.ExifTool() as et:
        list_of_metadata = [{'IMAGE_NAME':image, 'METADATA':et.get_metadata(image)} for image in list_of_files]

    #Create dataframe from list_of_metadata with image name in column and metadata in other column 
    df_images = pd.DataFrame(list_of_metadata)

    #Process images or files without metadata based on discard setting.
    print('Checking metadata tags of all images...')
    len_before_disc = len(df_images)
    keys = ['Composite:GPSDateTime', 'Composite:GPSLatitude', 'Composite:GPSLongitude', 'Composite:GPSAltitude']
    df_images[['GPS_DATETIME', 'LATITUDE', 'LONGITUDE', 'ALTITUDE']] = df_images.apply(lambda x: parse_metadata(x, keys, DISCARD), axis=1, result_type='expand')

    #remove discarded images.
    df_images.dropna(axis=0, how='any', inplace=True)
    #Reset index in case an image is dropped due to DISCARD
    df_images.reset_index(inplace = True, drop=True)
    print('{0} images dropped. "DISCARD" is {1}.\n'.format(len_before_disc - len(df_images), DISCARD))

    if len(df_images) == 0:
        print('All images were discarded. No images left to process. Exiting program.')
        input('Press any key to quit')
        quit()
    elif len(df_images) == 1:
        print('Only one image to process. No possible links. Exiting program.')
        input('Press any key to quit')
        quit()

    #Convert datetime from string to datetime format
    df_images['GPS_DATETIME'] = df_images.apply( lambda x: datetime.datetime.strptime(x['GPS_DATETIME'],'%Y:%m:%d %H:%M:%SZ'),axis=1)

    #Sort images
    df_images.sort_values(CONNECTION_TYPE, axis=0, ascending=True, inplace=True)

    #########################
    #Work with the resulting image dataframe to filter & find the right sequence

    #Calculate the time difference, distance and altitude difference with the NEXT image
    print('Calculating differences of time, distance and altitude between images...')
    for conn_type in ['DELTA_TIME', 'DISTANCE', 'DELTA_ALT']:
        df_images = calculate_to_next(df_images, conn_type)
        
    #Filter images, drop rows where needed and 
    #re-calculate the distance and altitude differences if rows are dropped
    print('Filtering images according to input parameters...')
    len_time = len(df_images)
    df_images = generic_connection(df_images, 'DELTA_TIME', MIN_TIME_INTERVAL) if TIME_FILTERING else df_images
    len_dist = len(df_images)
    print('{0} images discarded due to time spacing intervals'.format(len_time - len_dist))
    df_images = calculate_to_next(df_images, 'DISTANCE') if TIME_FILTERING else df_images
    df_images = generic_connection(df_images, 'DISTANCE', MIN_DISTANCE_INTERVAL) if DISTANCE_FITLERING else df_images
    len_alt = len(df_images)
    print('{0} images discarded due to distance spacing intervals'.format(len_dist - len_alt))
    df_images = calculate_to_next(df_images, 'DELTA_ALT') if DISTANCE_FITLERING else df_images
    df_images = generic_connection(df_images, 'DELTA_ALT', MIN_ALTITUDE_INTERVAL) if ALTITUDE_FITLERING else df_images
    len_final = len(df_images)
    print('{0} images discarded due to altitude spacing intervals\n'.format(len_alt - len_final))

    print('\nFinal amount of images to process: {0}\n\n'.format(len(df_images)))
    if len(df_images) == 0:
        print('All images were filtered out. No images left to process. Exiting program.')
        input('Press any key to quit')
        quit()
    elif len(df_images) == 1:
        print('Only one image left to process. No possible links. Exiting program.')
        input('Press any key to quit')
        quit()

    #Finally, calculate all differences again to their NEXT image
    print('Calculating final differences of time, distance and altitude between qualified images...')
    for conn_type in ['DELTA_TIME', 'DISTANCE', 'DELTA_ALT']:
        df_images = calculate_to_next(df_images, conn_type)
    
    #Calculate Azimuth (heading) and Pitch
    print('Calculating heading between qualified images....')
    df_images['AZIMUTH']  = df_images.apply(lambda x: calculate_initial_compass_bearing((x['LATITUDE'], x['LONGITUDE']), (x['LATITUDE_NEXT'], x['LONGITUDE_NEXT'])),axis=1)
    df_images.iat[-1, df_images.columns.get_loc('AZIMUTH')]  = df_images['AZIMUTH'].iloc[-2]
    df_images['PITCH']    = (df_images['ALTITUDE_NEXT'] - df_images['ALTITUDE']) / df_images['DISTANCE']

    #Add additional required data for output json.
    #All related to PREVIOUS image
    print('Setting related data of connected qualified images...')
    df_images['DISTANCE_TO_PREV']   = -1 * df_images['DISTANCE'].shift(1)
    df_images['DELTA_TIME_TO_PREV'] = -1 * df_images['DELTA_TIME'].shift(1)
    df_images['DELTA_ALT_TO_PREV']  = -1 * df_images['DELTA_ALT'].shift(1)
    df_images['PITCH_TO_PREV']      = -1 * df_images['PITCH'].shift(1)
    df_images['AZIMUTH_TO_PREV']    = (df_images['AZIMUTH'].shift(1) + 180) % 360

    df_images.iat[0, df_images.columns.get_loc('DELTA_ALT_TO_PREV')] = 0
    df_images.iat[0, df_images.columns.get_loc('DISTANCE_TO_PREV')] = 0
    df_images.iat[0, df_images.columns.get_loc('DELTA_TIME_TO_PREV')] = 0
    df_images.iat[0, df_images.columns.get_loc('AZIMUTH_TO_PREV')] = 0
    df_images.iat[0, df_images.columns.get_loc('PITCH_TO_PREV')] = 0
    
    #Add names of the NEXT and PREVIOUS image for quicker reference
    df_images['IMAGE_NAME_NEXT'] = df_images['IMAGE_NAME'].shift(-1)
    df_images['IMAGE_NAME_PREV'] = df_images['IMAGE_NAME'].shift(1)

    #Assign UUID
    df_images['UUID'] = df_images.apply(lambda x: str(uuid.uuid1()), axis=1)
    df_images['UUID_NEXT'] = df_images['UUID'].shift(-1)
    df_images['UUID_PREV'] = df_images['UUID'].shift(1)

    #Create the global JSON structure
    #Main keys will be the image to which the subkeys will be added to
    print('\nGenerating JSON object...')
    descriptions = {k['UUID']:{
                        'connections': {
                            k['UUID_NEXT']: {
                                 'distance_mtrs':k['DISTANCE'],
                                 'elevation_mtrs':k['DELTA_ALT'],
                                 'heading_deg':k['AZIMUTH'],
                                 'pitch_deg':k['PITCH'],
                                 'time_sec':k['DELTA_TIME']}, 

                            k['UUID_PREV']: {
                                 'distance_mtrs':k['DISTANCE_TO_PREV'],
                                 'elevation_mtrs':k['DELTA_ALT_TO_PREV'],
                                 'heading_deg':k['AZIMUTH_TO_PREV'],
                                 'pitch_deg':k['PITCH_TO_PREV'],
                                 'time_sec':k['DELTA_TIME_TO_PREV']}
                            },

                         'id':k['UUID'],
                         'create_date':datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d:%H:%M:%S'),
                         'software':'sequence-maker'
                         }
                    for index, k in df_images.iterrows()
                    }

    img_id_link = {k['UUID']:k['IMAGE_NAME'] for index, k in df_images.iterrows()}

    #Remove the 'nan' links of the first image to its PREVIOUS, and
    #the NEXT image of the last image
    to_del = []
    for image in descriptions.keys():
        for connection in descriptions[image]['connections'].keys():
            if type(connection) == float:
                to_del.append([image, connection])

    for z, y in to_del:
        del descriptions[z]['connections'][y] 


    #For each image, write the JSON into EXIF::ImageDescription
    print('Writing metadata to EXIF::ImageDescription of qualified images...\n')
    with exiftool.ExifTool() as et:
        for image_uuid in descriptions.keys():
            et.execute(bytes('-ImageDescription={0}'.format(json.dumps(descriptions[image_uuid])), 'utf-8'), bytes("{0}".format(img_id_link[image_uuid]), 'utf-8'))

    clean_up_new_files(OUTPUT_PHOTO_DIRECTORY, [image for image in img_id_link.values()])

    input('\nMetadata successfully added to images.\n\nPress any key to quit')
    quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'Image sequence metadata setter')

    parser.add_argument('-f', '--frame-rate', 
                        action='store', 
                        default='1000000',
                        dest='frame_rate',
                        help='Frame rate per second')

    parser.add_argument('-s', '--spatial-distance-min', 
                        action='store', 
                        default='0',
                        dest='spatial_distance_min',
                        help='Minimum linear distance between two images.')

    parser.add_argument('-a', '--altitude-difference-min', 
                        action='store', 
                        default='0',
                        dest='alt_diff_min',
                        help='Minimum altitude between two images.')

    parser.add_argument('-j', '--join-mode', 
                        action='store', 
                        default='time',
                        dest='join_mode',
                        help='Join images in a sequence based on "time" or "filename".')

    parser.add_argument('-d', '--discard', 
                        action='store_true', 
                        default=False,
                        dest='discard',
                        help='Force the program to continue if images do not have all required metadata. Such images will be discarded.')

    parser.add_argument('-e', '--exiftool-exec-path', 
                        action='store', 
                        default='No path specified',
                        dest='executable_path',
                        help='Optional: path to Exiftool executionable.')

    parser.add_argument('input_directory', 
                        action="store", 
                        help='Path to input folder.')
    parser.add_argument('output_directory', 
                        action="store", 
                        help ='Path to output folder.')

    parser.add_argument('--version', 
                        action='version', 
                        version='%(prog)s 1.0')

    args = parser.parse_args()

    make_sequence(args)


#args.__dict__ = {'frame_rate':'1000000', 'alt_diff_min':'100', 'spatial_distance_min': '0.5', 'join_mode':'filename', 'discard':True, 'executable_path': r"D:\Jasper\Py\automate.IT\trek-view\Trek-View\exiftool.exe", 'input_directory':r"D:\Jasper\Py\automate.IT\TEMP\TIMELAPSE\TIMELAPSE", 'output_directory': r"D:\Jasper\Py\automate.IT\TEMP\Output_s1"}
#__file__ = r'D:\Jasper\Py\automate.IT\trek-view\Trek-View\Sequence-Maker\sequence-maker.py'
#sys.path.append(r'D:\Jasper\Py\automate.IT\trek-view\Trek-View\Sequence-Maker\\')