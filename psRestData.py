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
from psRestUtilities import getUrl



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
			toUrl = getUrl ( url, rootResource, str( plan ), 'child', r )
			#log.info('\t%s ' % ( r ) )
			restOutput, t = getRest ( toUrl, log )
			filename = str( plan ) + '.' + r
			if restOutput[ 'items' ]:
				log.info('\t\t%5s Records \t%s sec \t%s' % (( len( restOutput[ 'items' ] ) ), t, r))
				writeCsv ( restOutput[ 'items' ], filename, outDir )

	
	
