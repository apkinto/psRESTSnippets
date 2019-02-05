import json
import requests
import datetime
import xml.etree.ElementTree as ET
import sys, os
import urllib.parse
import csv
import logging
from psRestUtilities import getTime
from psRestUtilities import setLogging
from psRestUtilities import setVariables
from psRestUtilities import getRest
from psRestUtilities import getResources
from psRestUtilities import getPsPlanId
from psRestUtilities import writeCsv



if __name__ == "__main__":
	
	log = setLogging()
	variables = setVariables('psRest.xml')
	outDir = variables['psOutputDirectory']
	inputDir = variables['psInputDirectory']
	resourceList = variables['resourceList']
	rootResource = variables['rootResource']
	url = variables['url']
	planId = variables['planId']
	resFile = os.path.join(inputDir, resourceList)	
	resources = getResources( resFile )
	
	psPlanIdList = getPsPlanId( url, rootResource, log )
	log.info('REST Server: %s\n' % ( url ))
	
	for plan in psPlanIdList:
		log.info( 'PlanId: %s ' % ( plan ) )
		for r in resources:
			params = [ str(plan), 'child', r ]
			toUrl = url + '/' + rootResource + '/' + '/'.join( params )
			log.info('\t%s ' % ( r ) )
			restOutput = getRest ( toUrl, log )
			filename = str( plan ) + '.' + r
			if restOutput[ 'items' ]:
				log.info('\t\t%s records' % ( len( restOutput[ 'items' ] ) ))
				writeCsv ( restOutput[ 'items' ], filename, outDir )

	
	
