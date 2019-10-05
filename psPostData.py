import sys, os
import json
import urllib.parse
from psRestUtilities import *

def postData ( objectList, url ):
	for object in objectList:
		#print ( object )
		#jsonData = json.dumps(object)
		print (object)
		t, status, statusText = postRest( url, session, object, requestHeader, authorization, log )
		log.info('\tPOST StatusCode: %s\t Time: \t%s sec \t%s' % ( status, t, t ) )

def updateAttribute( restCount ):
	start = getTime()
	attributeValues = getExcelData( excelData, 'AttributeValue' )
	#	get unique list of (<orgCode>, <SegCode>) from speradsheet
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in attributeValues )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in attributeValues )
	#print ('"""', segmentCodes)
	
	segmentXref={}
	
	for organization in uniqueOrgs:
		attrUrl = getUrl( psOrgUrl, str(orgXref[organization]), 'child/attributes' )
		psOrgAttr, t, status, restCount = getRest( attrUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for orgAttr in psOrgAttr['items']:
			attrKeys = getKey( orgAttr['links'] )
			segmentXref[orgAttr['SegmentCode']] = [orgAttr['AttributeId'], attrKeys]
	
	attrValXref = {}
	
	for segment in segmentCodes:	#Get attribute Values for each segment
		attrValUrl = getUrl( psOrgUrl, str(orgXref[segment[0]]), 'child/attributes', segmentXref[segment[1]][1], 'child/attributeValues' )
		psOrgAttrVal, t, status, restCount = getRest( attrValUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for attrVal in psOrgAttrVal['items']:
			attrValKeys = getKey( attrVal['links'] )
			attrValXref[ (segment[0], segment[1], attrVal['AttributeValueCode'] ) ] = [ attrVal['AttributeValueId'], attrValKeys ] 
	
	for av in attributeValues:
		attrColor={}
		attrColor['OrganizationId'] = orgXref[ av['OrganizationCode'] ]
		attrColor['AttributeId'] = segmentXref[ av['SegmentCode'] ][0]
		attrColor['AttributeValueId'] = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][0]
		attrColor['Color'] = av['Color']
		attrValKey = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][1]
		postAttrValueUrl = getUrl( psOrgUrl, str(orgXref[ av['OrganizationCode']]), 'child/attributes', segmentXref[av['SegmentCode']][1], 'child/attributeValues', attrValKey)
		#print ('ATTCOLOR', attrColor, postAttrValueUrl)
		t, status, statusText, restCount = patchRest( postAttrValueUrl, session, attrColor, requestHeader, authorization, log, restCount )

	print ( '***', restCount )
	end = getTime()
	time = end - start
	log.info('\t\tUpdated Attribute Colors in %s\tsec' % (time))
	print ('<<<<<<<')			

def updateAttributeColors( restCount ):
	start = getTime()
	attributeValues = getExcelData( excelData, 'AttributeValue' )
	for av in attributeValues:
		print ('\n\n>>>>>>>')
		''' For each row in the Excel, find the id's '''
		av['OrganizationId'] = orgXref[ av['OrganizationCode'] ]
		''' Make attribute call by organization to get attributeId '''
		attrUrl = getUrl( psOrgUrl, str(av['OrganizationId']), 'child/attributes' )
		psOrgAttr, t, status, restCount = getRest( attrUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount )
		#print ('excelSegmentCode', av['SegmentCode'])
		for attr in psOrgAttr['items']:
			#print ('attrSegmentCode', attr['SegmentCode'])
			''' Process only SegmentCodes defined in the spreadsheet and get the AttributeId '''
			if av['SegmentCode'] == attr['SegmentCode']:
				print ( "\t---", attr['SegmentCode'], attr['AttributeId'], '\n')
				''' Get the system generated Key for Attribute '''
				attrKey = getKey ( attr['links'] )
				attrValUrl = getUrl(attrUrl, attrKey, 'child/attributeValues')
				psOrgAttrVal, t, status, restCount = getRest( attrValUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount )
				print ('AttributeValue::', psOrgAttrVal['items'])
				for attrVal in psOrgAttrVal['items']:
					#print ( '\t--->', attr['SegmentCode'], attrVal['AttributeValueCode'], av['AttributeValueCode'] )
					if attrVal['AttributeValueCode'] == av['AttributeValueCode']:
						attrColor = {}
						attrValKey = getKey ( attrVal['links'] )
						postAttrValueUrl = getUrl(attrValUrl, attrValKey)
						attrColor['OrganizationId'] = av['OrganizationId']
						attrColor['AttributeId'] = attr['AttributeId']
						attrColor['AttributeValueId'] = attrVal['AttributeValueId']
						attrColor['Color'] = av['Color']
						print ('ATTCOLOR', attrColor)
						t, status, statusText, restCount = patchRest( postAttrValueUrl, session, attrColor, requestHeader, authorization, log, restCount )
	print ( '***', restCount )
	end = getTime()
	time = end - start
	log.info('\t\tUpdated Attribute Colors in %s\tsec' % (time))
	print ('<<<<<<<')	
	
						
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
	restCount = 0
	
	session, authorization, requestHeader, payload = scmAuth ( username, password )
	
	log.info('REST Server: %s' % ( url ))
	psPlanUrl = getUrl( url, rootResource)
	psOrgUrl = getUrl ( url, psOrg ) 
	
	'''	get Schedule Organizations and create code/id xref	'''
	psOrganizations, t, status, restCount = getRest ( psOrgUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount )
	orgXref = idCode ( psOrganizations, 'OrganizationCode', 'OrganizationId', log )
	#print ( orgXref )
	#for org in orgXref.items():
	#	print ( org )
	
	''' Get Existing Plan Information '''
	psPlanOutput, t, status, restCount = getRest( psPlanUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
	psPlanIdList = getPsPlanId( psPlanOutput, log )	
	#print ( psPlanIdList ) 
	
	'''
		Create Production Scheduling Plans
	'''
	
	'''  Read data from Excel worksheet '''
	plans = getExcelData( excelData, 'Plans' )
	
	'''	For each plan, insert OrgId	'''
	#print (plans)
	for plan in plans:
		#plan.pop('PlanId')
		plan['OrganizationId'] = orgXref[ plan['OrganizationCode'] ]
	#print ( plans )
	
	#postData( plans, psPlanUrl )  #Create Plans
	#updateAttributeColors( restCount )
	updateAttribute( restCount )
