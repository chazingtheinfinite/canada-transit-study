""" File: auto-GTFS-downloader.py
Author: Kevin Dick
Date: 2022-05-16
---
Description: Script to automatically download the GTFS data from the links
provided in the inventory Excel file.
"""
import os, sys
from time import sleep
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description='')
parser.add_argument('-i', '--input', required=True,
                    help='input inventory file')
parser.add_argument('-o', '--output_dir', required=True,
                    help='output root directory where all CSD data are stored')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase verbosity')
args = parser.parse_args()

# EXAMPLE: python3 auto-GTFS-downloader.py -i ../data/inventory-final.xlsx -o ../data/CSDs/ -v


LABEL_COL = 'PN/PT'
DELAY = 2

def get_URL_type(candidate):
	""" get_URL_type 
		Takes in a DataFrame row and maps it to the type of 
		GTFS data record that it represents; one of:
		- Static_GTFS 
		- Realtime_GTFS 
		- CSV 
		- KML 
		- ShapeFile
		- GeoJSON
		- Map_PDF_JPEG
		- Other
	"""
	label_col = candidate[LABEL_COL].lower()
	data_col  = candidate[-1]
	if   'url1' in label_col: return ('Other', data_col)
	elif 'url2' in label_col: return ('Other', data_col)
	elif 'static' in label_col: return ('Static_GTFS', data_col)
	elif 'real' in label_col: return ('Realtime_GTFS', data_col)
	elif 'csv' in label_col: return ('CSV', data_col)
	elif 'kml' in label_col: return ('KML', data_col)
	elif 'shapefile'in label_col: return ('ShapeFile', data_col)
	elif 'geojson' in label_col: return ('GeoJSON', data_col)
	elif 'pdf' in label_col: return ('Map_PDF_JPEG', data_col)
	else: sys.exit(f'Failed mapping on entry: {candidate}') 

def process_sheet(sheet_df):
	""" process_sheet
		Takes in the sheet DataFrame, parses out the URL if .ZIP format,
		and saves the data to the specific CSD location.
	"""
	#if args.verbose: print(sheet_df)
	urls = []

	# Get the indecies that might have a url 
	temp = sheet_df[sheet_df[LABEL_COL].str.lower().str.contains("url", na=False)]
	temp2 = temp[temp.iloc[: , -1].notna()]
	print(temp2)

	# Map the url entires to a consistent type for sub-dir organization
	for index, row in temp2.iterrows():
		if not row.empty: urls.append(get_URL_type(row))

	return urls

def download_gtfs_data(url, subdir):
	""" download_gtfs_data
		Attempt to acquire the GTFS resource based on the pointing URL.
		
		Special cases:
		1) if a 'transitfeeds' link, must append "/latest/download" 
		2) erroneous urls, such as descriptions instead of links, must be skipped
	"""
	# Skip instances with mis-formatted or errorneous urls
	if ' ' in url: return

	# Correct the transitfeeds-type urls to contain a download suffix
	if 'transitfeeds' in url and not '/latest/download' in url: url += '/latest/download'

	# Regardless of success or failure, a link to the intended source is saved to the subdir
	open(os.path.join(subdir, 'source-url.txt'), 'w').write(url)
	
	download_cmd = f'wget -P {subdir} {url}'
	if args.verbose: print(f'Attempting download of {url} with cmd:\n{download_cmd}')
	os.system(download_cmd)
	sleep(DELAY)

def main():
	""" main function """
	xls = pd.ExcelFile(args.input)
	if args.verbose: print(f'There are {len(xls.sheet_names)} sheets')
	
	# We will append stats to this dict as we go along
	sum_stats = { 'num_CSDs' : 0,
		      'num_with_URL': 0
		}

	for idx, sheet in enumerate(xls.sheet_names[1:]): # Skip the first overview sheet 
		# Process each sheet
		if "Sheet" in sheet: continue # Skip those that are not CSDs
		if args.verbose: print(f'\n{"-"*10} ({idx}/{len(xls.sheet_names)}) {"-"*10}\nProcessing {sheet}')
		urls = process_sheet(xls.parse(sheet))

		# Create subdir stucture based on available urls
		# First create a CSD-specific subdir
		csd_dir = os.path.join(args.output_dir, sheet.replace(',', '').replace(' ', '-'))
		if not os.path.exists(csd_dir): 
			if args.verbose: print(f'Making {csd_dir}')
			os.mkdir(csd_dir)
		for gtfs_type, url in urls:
			# Create a subdir based on the GTFS data type
			gtfs_dir = os.path.join(csd_dir, gtfs_type)
			if not os.path.exists(gtfs_dir): 
				if args.verbose: print(f'Making {gtfs_dir}')
				os.mkdir(gtfs_dir)
			
			# download the data to the specific subdir location		
			download_gtfs_data(url.strip(' '), gtfs_dir)
			
			# update stats
			sum_stats[gtfs_type] = sum_stats.get(gtfs_type, 0) + 1

		# Update the summary statistics
		sum_stats['num_CSDs'] = sum_stats['num_CSDs'] + 1
		if len(urls) >= 1: sum_stats['num_with_URL'] = sum_stats['num_with_URL'] + 1

	print(sum_stats)

if __name__ == "__main__": main()
