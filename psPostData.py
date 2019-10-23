import sys, os
import json
import urllib.parse
from psRestUtilities import *
import datetime
import time


def postData ( objectList, url ):
	for object in objectList:
		t, status, statusText = postRest( url, session, object, requestHeader, authorization, log )
		log.info('\t\t\tStatusCode: %s\t TotalTime: \t%s sec \t%s' % ( status, t, t ) )
		
def createPlans ( psPlanUrl, restCount ):
	plans = getExcelData( excelFile, 'Plans' )
	
	''' Get Existing Plan Information '''
	psPlanOutput, t, status, restCount = getRest( psPlanUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
	psPlanIdList = getPsPlanId( psPlanOutput, log )	
		
	'''	For each plan that does not already exist, insert OrgId	'''
	for plan in plans:
		if plan['PlanName'] in ( [dict['PlanName'] for dict in psPlanIdList] ):
			log.info('\t\t**Plan %s already exists, skipping' % ( plan['PlanName'] ) )
		else:
			#plan.pop('PlanId')
			plan['OrganizationId'] = orgXref[ plan['OrganizationCode'] ]
			log.info('\tCreating Plan %s' % ( plan['PlanName'] ) )
			t, status, statusText, restCount = postRest( psPlanUrl, session, plan, requestHeader, authorization, log, restCount )
			
def segmentXreference ( orgs, segCodes, restCount ):
	segmentCodeIdXref ={}	
	for org in orgs:
		log.info('\t\t-->\tAttributeCode AttributeID Cross reference for %s ' % (segCodes))
		attrUrl = getUrl( psOrgUrl, str(orgXref[org]), 'child/attributes' )
		psOrgAttr, t, status, restCount = getRest( attrUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for orgAttr in psOrgAttr['items']:
			attrKeys = getKey( orgAttr['links'] )
			segmentCodeIdXref[orgAttr['SegmentCode']] = [orgAttr['AttributeId'], attrKeys]
	
	return segmentCodeIdXref
	
def attributeValXreference ( segCodes, segXref, restCount ):
	attributeValueXref = {}
	for segment in segCodes:	
		log.info('\t\t-->AttributeValueCode AttributeValueID Cross reference for %s' % (str(segment)))
		attrValUrl = getUrl( psOrgUrl, str(orgXref[segment[0]]), 'child/attributes', segXref[segment[1]][1], 'child/attributeValues' )
		psOrgAttrVal, t, status, restCount = getRest( attrValUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for attrVal in psOrgAttrVal['items']:
			attrValKeys = getKey( attrVal['links'] )
			attributeValueXref[ (segment[0], segment[1], attrVal['AttributeValueCode'] ) ] = [ attrVal['AttributeValueId'], attrValKeys ] 
	
	return attributeValueXref
	
def updateAttribute( restCount ):
	log.info('\tUpdating AttributeValue Colors')
	start = getTime()
	attributeValues = getExcelData( excelFile, 'AttributeValue' )
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in attributeValues )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in attributeValues )
	
	segmentXref = segmentXreference( uniqueOrgs, segmentCodes, restCount )
	attrValXref = attributeValXreference( segmentCodes, segmentXref, restCount )  

	for av in attributeValues:
		log.info('\t\t-->Updating Attribute Colors for %s: %s' % (av['SegmentCode'], av['AttributeValueCode']))
		attrColor={}
		attrColor['OrganizationId'] = orgXref[ av['OrganizationCode'] ]
		attrColor['AttributeId'] = segmentXref[ av['SegmentCode'] ][0]
		attrColor['AttributeValueId'] = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][0]
		attrColor['Color'] = av['Color']
		attrValKey = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][1]
		postAttrValueUrl = getUrl( psOrgUrl, str(orgXref[ av['OrganizationCode']]), 'child/attributes', segmentXref[av['SegmentCode']][1], 'child/attributeValues', attrValKey)
		t, status, statusText, restCount = patchRest( postAttrValueUrl, session, attrColor, requestHeader, authorization, log, restCount )

	end = getTime()
	TotalTime = end - start
	log.info('\t\tUpdated Attribute Colors %s REST calls in %s\tsec' % (restCount, TotalTime))

def createChangeoversBatch( restCount ):
	log.info('\tCreating Changeovers')
	start = getTime()
	changeOvers = getExcelData( excelFile, 'Changeovers' )
	workCenters = set( dict['WorkCenterCode'] for dict in changeOvers )
	resources = set( dict['Resource'] for dict in changeOvers )
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in changeOvers )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in changeOvers )
	wcUrl = getUrl ( url, 'workCenters' ) 
	mfgWorkCenters, t, status, restCount = getRest ( wcUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount )
	#Assumes work center ID is the same across orgs, if not need to add org as key
	wcXref = idCode ( mfgWorkCenters, 'WorkCenterCode', 'WorkCenterId', log )
	
	resourceXref = {}
	for wc in workCenters:
		log.info('\t\t-->ResourceName ResourceID Cross reference for resources in %s' % (str(wc)))
		wcResourceUrl = getUrl( wcUrl, str(wcXref[wc]), 'child/WorkCenterResource' )
		wcResource, t, status, restCount = getRest( wcResourceUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for resource in wcResource['items']:
			resourceXref[ resource['ResourceName'] ] = resource['ResourceId']
	
	segmentXref = segmentXreference( uniqueOrgs, segmentCodes, restCount )
	attrValXref = attributeValXreference( segmentCodes, segmentXref, restCount ) 
	
	changeoverId = int(time.mktime(datetime.datetime.now().timetuple())*100000)
	changeoverSeq = changeoverId
	
	partsList = []
	for co in changeOvers:
		parts = {}
		coPayload ={}
		coPayload['OrganizationId'] = orgXref[ co['OrganizationCode' ] ]
		coPayload['ChangeoverId'] = changeoverId
		#coPayload['ChangeoverSequenceNumber'] = co['ChangeoverSequenceNumber' ]
		coPayload['ChangeoverSequenceNumber'] = changeoverSeq
		coPayload['WorkCenterId'] = wcXref[ co['WorkCenterCode'] ]
		coPayload['ResourceId'] = resourceXref[ co['Resource'] ]
		coPayload['AttributeId'] = segmentXref[ co['SegmentCode'] ][0]
		coPayload['FromAttributeValueId'] = attrValXref[ (co['OrganizationCode' ], co['SegmentCode'], co['FromAttributeValueCode']) ][0]
		coPayload['ToAttributeValueId'] = attrValXref[ (co['OrganizationCode' ], co['SegmentCode'],co['ToAttributeValueCode']) ][0]
		coPayload['Duration'] = co['Duration']
		coPayload['DurationUnit'] = co['DurationUnit']
		coPayload['Cost'] = 1
		parts = getParts(changeoverId, getUrl('/productionSchedulingOrganizations', str(orgXref[co['OrganizationCode']]), 'child/changeoverRules'), 'create', coPayload)
		partsList.append(parts)
		changeoverId += 1
		changeoverSeq += 1
		
	log.info('\t\tCreating %s Changeover Records in batches of %s' % (len(partsList), batchChunks))
	t, status, statusText, restCount = postBatchRest( url, session, partsList, int(batchChunks), authorization, log, restCount )
	end = getTime()
	TotalTime = end - start
	log.info('\t\tChangeovers:: %s REST calls in %s\tsec' % (restCount, TotalTime))


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
	
	#createPlans( psPlanUrl, restCount) 
	#updateAttribute( restCount )
	#createChangeovers( restCount )
	createChangeoversBatch( restCount )
