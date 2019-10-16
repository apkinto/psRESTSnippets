import sys, os
import json
import urllib.parse
from psRestUtilities import *

def postData ( objectList, url ):
	for object in objectList:
		t, status, statusText = postRest( url, session, object, requestHeader, authorization, log )
		log.info('\t\t\tStatusCode: %s\t Time: \t%s sec \t%s' % ( status, t, t ) )
		
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
	time = end - start
	log.info('\t\tUpdated Attribute Colors %s REST calls in %s\tsec' % (restCount, time))

def createChangeovers( restCount ):
	log.info('\tCreating Changeovers')
	start = getTime()
	changeOvers = getExcelData( excelFile, 'Changeovers' )
	#print (changeOvers)
	workCenters = set( dict['WorkCenterCode'] for dict in changeOvers )
	resources = set( dict['Resource'] for dict in changeOvers )
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in changeOvers )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in changeOvers )
	
	'''
	uniqueFromAttr = set( (dict['SegmentCode'], dict['FromAttributeValueCode']) for dict in changeOvers )
	uniqueToAttr = set( (dict['SegmentCode'], dict['ToAttributeValueCode']) for dict in changeOvers )
	#Get a unique set of From/To attribute values
	uniqueAttrVal = uniqueFromAttr.copy()
	uniqueAttrVal.update(uniqueToAttr)
	'''
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
	
	#The following is to get the Max ChangeoverId and MaxCOSequence Number...need change REST so coId is not requried on POST.  Also, consider making seq num as an input in the spreadsheet instead of just incrementing by max+100
	coId = []
	coSeq = []
	for org in uniqueOrgs:
		postCOUrl = getUrl( psOrgUrl, str(orgXref[org]), 'child/changeoverRules' )
		currentCo, t, status, restCount = getRest( postCOUrl, session, payload, requestHeader, authorization, recordLimit, log, restCount)
		for c in (currentCo['items']):
			coId.append( c['ChangeoverId'] )
			coSeq.append( c['ChangeoverSequenceNumber'] )
	
	changeoverId = max(coId) + 1
	changeoverSeq = max(coSeq) + 100

	for co in changeOvers:
		changeOverBody ={}
		changeOverBody['OrganizationId'] = orgXref[ co['OrganizationCode' ] ]
		changeOverBody['ChangeoverId'] = changeoverId
		#changeOverBody['ChangeoverSequenceNumber'] = co['ChangeoverSequenceNumber' ]
		changeOverBody['ChangeoverSequenceNumber'] = changeoverSeq
		changeOverBody['WorkCenterId'] = wcXref[ co['WorkCenterCode'] ]
		changeOverBody['ResourceId'] = resourceXref[ co['Resource'] ]
		changeOverBody['AttributeId'] = segmentXref[ co['SegmentCode'] ][0]
		changeOverBody['FromAttributeValueId'] = attrValXref[ (co['OrganizationCode' ], co['SegmentCode'], co['FromAttributeValueCode']) ][0]
		changeOverBody['ToAttributeValueId'] = attrValXref[ (co['OrganizationCode' ], co['SegmentCode'],co['ToAttributeValueCode']) ][0]
		changeOverBody['Duration'] = co['Duration']
		changeOverBody['DurationUnit'] = co['DurationUnit']
		changeOverBody['Cost'] = 1
		changeoverId += 1
		changeoverSeq += 100
		log.info('\t\tCreating Changeover Record')
		postCOUrl = getUrl( psOrgUrl, str(orgXref[ co['OrganizationCode']]), 'child/changeoverRules' )
		t, status, statusText, restCount = postRest( postCOUrl, session, changeOverBody, requestHeader, authorization, log, restCount )
		log.info('\t\t-->%s' % (status))
	
	end = getTime()
	time = end - start
	log.info('\t\tChangeovers:: %s REST calls in %s\tsec' % (restCount, time))
						
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
	updateAttribute( restCount )
	createChangeovers( restCount )
