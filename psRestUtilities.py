import json
import requests
import datetime
import xml.etree.ElementTree as ET
import sys, os
import urllib.parse
import csv
import logging


def getTime():
	currentTime = datetime.datetime.now()
	return currentTime

def setVariables( config ):
	'''
		Sets variables from psPythonConfig.xml.   Currently assumes it is in the PS bin directory.
	'''
	variable = {}
	config = ET.parse(config)
	root = config.getroot()
	for var in root.find('variableList'):
		variable[var.tag] = var.text
	return variable

def setLogging():
	logger = logging.getLogger(__name__)
	logger.setLevel(logging.DEBUG)
	
	fh = logging.FileHandler('psPython.log')
	fh.setLevel(logging.INFO)
	
	ch = logging.StreamHandler()
	ch.setLevel(logging.INFO)
	
	formatter = logging.Formatter('%(asctime)s %(name)s  %(levelname)s \t %(message)s')
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)
	
	logger.addHandler(fh)
	logger.addHandler(ch)
	return logger
		
def getRest( url, log ):
	#log = setLogging()
	#newUrl = urllib.parse.urljoin( url, 'productionSchedulingPlans/describe' )
	data = ''
	start = getTime()
	r = requests.get( url, data=data )
	data = r.content
	output = json.loads(data)
	end = getTime()
	log.info('\t\t%s sec' % (end-start))
	
	return output
		
def getResources( filename ):
	resourceNames = []
	with open(filename, 'r', newline = '') as f:  
		for line in f:
			resourceNames.append(line.rstrip())
	return resourceNames

def getPsPlanId ( url, rootResource, log ):
	#log = setLogging()
	psPlans = []
	psPlanUrl = url + '/' + rootResource 
	psPlanOutput = getRest( psPlanUrl, log )
	for p in psPlanOutput['items']:
		psPlans.append( p['PlanId'] )
	
	log.info('Fetching for following Plans (PlanID): %s ' % ( psPlans ) )
	return psPlans
	
def writeCsv ( list, filename, outDir ):
	file = filename + '.csv'
	csvFile = os.path.join( outDir, file)
	with open( csvFile, 'w', newline = '' ) as f:
		header = []
		for h in list[0].keys():
			header.append( h )
		csvwriter= csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		csvwriter.writerow( header )
		for i in list:
			w = csv.DictWriter(f, i.keys())
			w.writerow(i)
		f.close()


if __name__ == "__main__":

