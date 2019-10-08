import sys, os
import json
import urllib.parse
from psRestUtilities import *

def postData ( objectList, url ):
	for object in objectList:
		t, status, statusText = postRest( url, session, object, requestHeader, authorization, log )
		log.info('\tPOST StatusCode: %s\t Time: \t%s sec \t%s' % ( status, t, t ) )
		
def createPlans ( psPlanUrl, restCount ):
	plans = getExcelData( excelFile, 'Plans' )
	
	''' Get Existing Plan Information '''
	psPlanOutput, t, status, restCount = getRest( psPlanUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
	psPlanIdList = getPsPlanId( psPlanOutput, log )	
		
	'''	For each plan that does not already exist, insert OrgId	'''
	for plan in plans:
		if plan['PlanName'] in ( [dict['PlanName'] for dict in psPlanIdList] ):
			log.info('\t**Plan %s already exists, skipping' % ( plan['PlanName'] ) )
		else:
			#plan.pop('PlanId')
			plan['OrganizationId'] = orgXref[ plan['OrganizationCode'] ]
			log.info('\tCreating Plan %s' % ( plan['PlanName'] ) )
			t, status, statusText, restCount = postRest( psPlanUrl, session, plan, requestHeader, authorization, log, restCount )
		
def updateAttribute( restCount ):
	log.info('\tUpdating AttributeValue Colors')
	start = getTime()
	attributeValues = getExcelData( excelFile, 'AttributeValue' )
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in attributeValues )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in attributeValues )
	
	segmentXref={}
	
	for organization in uniqueOrgs:
		log.info('\tCreating AttributeCode AttributeID Cross reference for %s ' % (segmentCodes))
		attrUrl = getUrl( psOrgUrl, str(orgXref[organization]), 'child/attributes' )
		psOrgAttr, t, status, restCount = getRest( attrUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for orgAttr in psOrgAttr['items']:
			attrKeys = getKey( orgAttr['links'] )
			segmentXref[orgAttr['SegmentCode']] = [orgAttr['AttributeId'], attrKeys]
	
	attrValXref = {}
	
	for segment in segmentCodes:	
		log.info('\tCreating AttributeValueCode AttributeValueID Cross reference for %s' % (str(segment)))
		attrValUrl = getUrl( psOrgUrl, str(orgXref[segment[0]]), 'child/attributes', segmentXref[segment[1]][1], 'child/attributeValues' )
		psOrgAttrVal, t, status, restCount = getRest( attrValUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for attrVal in psOrgAttrVal['items']:
			attrValKeys = getKey( attrVal['links'] )
			attrValXref[ (segment[0], segment[1], attrVal['AttributeValueCode'] ) ] = [ attrVal['AttributeValueId'], attrValKeys ] 
	
	for av in attributeValues:
		log.info('\tUpdating Attribute Colors for %s: %s' % (av['SegmentCode'], av['AttributeValueCode']))
		attrColor={}
		attrColor['OrganizationId'] = orgXref[ av['OrganizationCode'] ]
		attrColor['AttributeId'] = segmentXref[ av['SegmentCode'] ][0]
		attrColor['AttributeValueId'] = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][0]
		attrColor['Color'] = av['Color']
		attrValKey = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][1]
		postAttrValueUrl = getUrl( psOrgUrl, str(orgXref[ av['OrganizationCode']]), 'child/attributes', segmentXref[av['SegmentCode']][1], 'child/attributeValues', attrValKey)
		t, status, statusText, restCount = patchRest( postAttrValueUrl, session, attrColor, requestHeader, authorization, log, restCount )

	end = getTime()
	time = end - start
	log.info('\t\tUpdated Attribute Colors %s REST calls in %s\tsec' % (restCount, time))
	print ('<<<<<<<')			
	
						
if __name__ == "__main__":
	
	'''	Set Variables, logging, and establish Session 	'''
	log = setLogging()
	variables = setVariables('psRest.xml')
	for key,val in variables.items():
		exec(key + '=val')	
	session, authorization, requestHeader, payload = scmAuth ( user, password )
	
	log.info('REST Server: %s' % ( url ))
	psOrgUrl = getUrl ( url, psOrganizationsRoot ) 
	psPlanUrl = getUrl( url, rootResource)
	restCount = 0
	
	'''	get Schedule Organizations and create code/id xref	'''
	psOrganizations, t, status, restCount = getRest ( psOrgUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount )
	orgXref = idCode ( psOrganizations, 'OrganizationCode', 'OrganizationId', log )
	
	createPlans( psPlanUrl, restCount) 
	updateAttribute( restCount )
