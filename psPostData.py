import sys, os

import json
from psRestUtilities import *

def postData ( objectList, url ):

	for object in objectList:
		#print ( object )
		#jsonData = json.dumps(object)
		t, status, statusText = postRest( url, session, object, requestHeader, authorization, log )
		log.info('\tPOST StatusCode: %s\t Time: \t%s sec \t%s' % ( status, t, t ) )

if __name__ == "__main__":
	
	'''	Set Variables, logging, and establish Session 	'''
	log = setLogging()
	variables = setVariables('psRest.xml')
	outDir = variables['psOutputDirectory']
	inputDir = variables['psInputDirectory']
	rootResource = variables['rootResource']
	recordLimit = variables['recordLimit']
	url = variables['url']
	excelFile = variables['excelFile']
	excelData = os.path.join(inputDir, excelFile)	
	username = variables['user']
	password = variables['password']
	psOrg = variables['psOrganizationsRoot']
	
	session, authorization, requestHeader, payload = scmAuth ( username, password )
	
	log.info('REST Server: %s' % ( url ))
	psPlanUrl = getUrl( url, rootResource)
	psOrgUrl = getUrl ( url, psOrg ) 
	
	'''	get Schedule Organizations and create code/id xref	'''
	psOrganizations, t, status = getRest ( psOrgUrl, session, payload, requestHeader, authorization, recordLimit, log )
	orgXref = idCode ( psOrganizations, 'Organization', 'Code', log )
	#print ( orgXref )
	#for org in orgXref.items():
	#	print ( org )
	
	''' Get Existing Plan Information '''
	psPlanOutput, t, status = getRest( psPlanUrl, session, payload, requestHeader, authorization, recordLimit, log )
	psPlanIdList = getPsPlanId( psPlanOutput, log )	
	#print ( psPlanIdList ) 
	
	'''
		Create Production Scheduling Plans
	'''
	
	'''  Read data from Excel worksheet '''
	plans = readExcel( excelData, 'Plans' )
	
	'''	For each plan, insert OrgId	'''
	for plan in plans:
		plan.pop('PlanId')
		plan['OrganizationId'] = orgXref[ plan['OrganizationCode'] ]
	#print ( plans )
	
	#postData( plans, psPlanUrl )
	
	''' 
		Update Attribute Colors
	'''
	
	attributeValues = readExcel( excelData, 'AttributeValue' )
	#print ( '===', attributeValues )
	for av in attributeValues:
		''' For each row in the Excel, find the id's '''
		av['OrganizationId'] = orgXref[ av['OrganizationCode'] ]
		''' Make attribute call by organization to get attributeId '''
		attrUrl = getUrl( psOrgUrl, str(av['OrganizationId']), 'child/attributes' )
		psOrgAttr, t, status = getRest( attrUrl, session, payload, requestHeader, authorization, recordLimit, log )
		for attr in psOrgAttr['items']:
			''' Process only SegmentCodes defined in the spreadsheet and get the AttributeId '''
			if av['SegmentCode'] == attr['SegmentCode']:
				print ("---", attr['SegmentCode'], attr['AttributeId'])
				''' Get the system generated Key for Attribute '''
				for attrLink in attr['links']:
					if ( attrLink['rel'] == 'self' ):
						attrKey = parseUrl( attrLink['href'] )
						#print (attrKey)
						attrValUrl = getUrl(attrUrl, attrKey, 'child/attributeValues')
						psOrgAttrVal, t, status = getRest( attrValUrl, session, payload, requestHeader, authorization, recordLimit, log )
						for attrVal in psOrgAttrVal['items']:
							if attrVal['AttributeValueCode'] == av['AttributeValueCode']:
							#print (attrVal)
								print (av['OrganizationId'], attr['AttributeId'], attrVal['AttributeValueId'], av['Color'])
						
		#print ( psOrgAttr )
		

	