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
	
	log.info('REST Server: %s' % ( url ))	
	psPlanIdList = getPsPlanId( url, rootResource, log )

	
	for plan in psPlanIdList:
		log.info( 'PlanId: %s ' % ( plan ) )
		planUrl = getUrl ( url, rootResource, str( plan ) )
		planDetails, t, status = getRest ( planUrl, log )
		filename = str( plan ) + '.' + rootResource
		writeCsv ( [planDetails], filename, outDir )
		log.info('\t\tStatusCode: %s\t%5s Records \t%s sec \t%s' % (status, ( len( [ planDetails ] )), t, rootResource))
		for r in resources:
			toUrl = getUrl ( url, rootResource, str( plan ), 'child', r )
			restOutput, t, status = getRest ( toUrl, log )
			filename = str( plan ) + '.' + r
			if restOutput[ 'items' ]:
				log.info('\t\tStatusCode: %s\t%5s Records \t%s sec \t%s' % (status, ( len( restOutput[ 'items' ] )), t, r))
				writeCsv ( restOutput[ 'items' ], filename, outDir )
			else:
				log.info('\t\tStatusCode: %s\t%5s Records \t%s sec \t%s' % ( status, '-', t, r ) )

	
	
