import sys, os
import json
import urllib.parse
from oraRESTTools import *
import datetime
import time

def segmentXreference ( orgs, segCodes, restCount ):
	segmentCodeIdXref ={}	
	for org in orgs:
		log.info('\t\t-->\tAttributeCode AttributeID Cross reference for %s ' % (segCodes))
		attrUrl = getUrl( psOrgUrl, str(orgXref[org]), 'child/attributes' )
		psOrgAttr, t, status, statusText, restCount = getRest( attrUrl, session, payload, None, requestHeader, authorization, recordLimit, log, restCount)
		for orgAttr in psOrgAttr['items']:
			attrKeys = getKey( orgAttr['links'] )
			#print(orgAttr['SegmentCode'],"\t\t", attrKeys)
			segmentCodeIdXref[orgAttr['SegmentCode']] = [orgAttr['AttributeId'], attrKeys, orgAttr['AttributeCode']]
	
	return segmentCodeIdXref
	
def attributeValXreference ( segCodes, segXref, restCount ):
	attributeValueXref = {}
	for segment in segCodes:	
		log.info('\t\t-->AttributeValueCode AttributeValueID Cross reference for %s' % (str(segment)))
		attrValUrl = getUrl( psOrgUrl, str(orgXref[segment[0]]), 'child/attributes', segXref[segment[1]][1], 'child/attributeValues' )
		psOrgAttrVal, t, status, statusText, restCount = getRest( attrValUrl, session, payload, None, requestHeader, authorization, recordLimit, log, restCount)
		for attrVal in psOrgAttrVal['items']:
			attrValKeys = getKey( attrVal['links'] )
			#print (attrVal['AttributeValueCode'], "\t", attrValKeys)
			attributeValueXref[ (segment[0], segment[1], attrVal['AttributeValueCode'] ) ] = [ attrVal['AttributeValueId'], attrValKeys ] 
	
	return attributeValueXref

def createChangeoversBatch( restCount ):
	log.info('\tCreating Changeovers')
	start = getTime()
	changeOvers = getExcelData( excelFile, 'Changeovers' )
	workCenters = set( dict['WorkCenterCode'] for dict in changeOvers )
	resources = set( dict['Resource'] for dict in changeOvers )
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in changeOvers )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in changeOvers )
	wcUrl = getUrl ( url, 'workCenters' ) 
	mfgWorkCenters, t, status, statusText, restCount = getRest ( wcUrl, mfgsession, payload, None, mfgrequestHeader, mfgauthorization, recordLimit, log, restCount )
	wcXref = idCode ( mfgWorkCenters, 'WorkCenterCode', 'WorkCenterId', log )

	resourceXref = {}
	for wc in workCenters:
		log.info('\t\t-->ResourceName ResourceID Cross reference for resources in %s' % (str(wc)))
		wcResourceUrl = getUrl( wcUrl, str(wcXref[wc]), 'child/WorkCenterResource' )
		wcResource, t, status, statusText, restCount = getRest( wcResourceUrl, mfgsession, payload, None, mfgrequestHeader, mfgauthorization, recordLimit, log, restCount)
		for resource in wcResource['items']:
			resourceXref[ resource['ResourceName'] ] = resource['ResourceId']
	
	segmentXref = segmentXreference( uniqueOrgs, segmentCodes, restCount )
	attrValXref = attributeValXreference( segmentCodes, segmentXref, restCount ) 
	changeoverSeq=int(time.mktime(datetime.datetime.now().timetuple())*100000)
	
	partsList = []
	for co in changeOvers:
		parts = {}
		coPayload ={}
		coPayload['OrganizationId'] = orgXref[ co['OrganizationCode' ] ]
		coPayload['ChangeoverSequenceNumber'] = changeoverSeq
		coPayload['WorkCenterId'] = wcXref[ co['WorkCenterCode'] ]
		coPayload['WorkCenterCode'] = co['WorkCenterCode']
		coPayload['ResourceId'] = resourceXref[ co['Resource'] ]
		coPayload['ResourceCode'] = co['Resource']
		coPayload['AttributeId'] = segmentXref[ co['SegmentCode'] ][0]
		coPayload['AttributeCode'] = segmentXref[ co['SegmentCode'] ][2]
		coPayload['FromAttributeValueId'] = attrValXref[ (co['OrganizationCode' ], co['SegmentCode'], co['FromAttributeValueCode']) ][0]
		coPayload['FromAttributeValueCode'] = co['FromAttributeValueCode']
		coPayload['ToAttributeValueId'] = attrValXref[ (co['OrganizationCode' ], co['SegmentCode'],co['ToAttributeValueCode']) ][0]
		coPayload['ToAttributeValueCode'] = co['ToAttributeValueCode']
		coPayload['Duration'] = co['Duration']
		coPayload['DurationUnit'] = co['DurationUnit']
		coPayload['Cost'] = 1
		parts = getParts(changeoverSeq, getUrl('/productionSchedulingOrganizations', str(orgXref[co['OrganizationCode']]), 'child/changeoverRules'), 'create', coPayload)
		partsList.append(parts)
		changeoverSeq += 1
		
	log.info('\t\tCreating %s Changeover Records in batches of %s' % (len(partsList), batchChunks))
	t, status, statusText, restCount = postBatchRest( url, session, partsList, int(batchChunks), authorization, log, restCount )
	TotalTime = getTime() - start
	log.info('\t\tChangeovers:: %s REST calls in %s\tsec' % (restCount, TotalTime))

if __name__ == "__main__":
	
	'''	Set Variables, logging, and establish Session 	'''
	log = setLogging()
	variables = setVariables('psRest.xml')
	for key,val in variables.items():
		exec(key + '=val')	

	session, authorization, requestHeader, payload = scmAuth ( user, password )
	mfgsession, mfgauthorization, mfgrequestHeader, mfgpayload = scmAuth ( mfgUser, password )
	
	log.info('REST Server: %s' % ( url ))
	psOrgUrl = getUrl ( url, 'productionSchedulingOrganizations' ) 
	psPlanUrl = getUrl( url, 'productionSchedulingPlans')
	restCount = 0
	
	'''	get Schedule Organizations and create code/id xref	'''
	psOrganizations, t, status, statusText, restCount = getRest ( psOrgUrl, session, payload, None, requestHeader, authorization, recordLimit, log, restCount )
	orgXref = idCode ( psOrganizations, 'OrganizationCode', 'OrganizationId', log )
	
	createChangeoversBatch (restCount)
