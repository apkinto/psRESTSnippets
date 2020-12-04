import sys, os
import json
import urllib.parse
from oraRESTTools import *
import datetime
import time


def postData ( objectList, url ):
	for object in objectList:
		output, t, status, statusText = postRest( url, session, object, requestHeader, authorization, log )
		log.info('\t\t\tStatusCode: %s\t TotalTime: \t%s sec \t%s' % ( status, t, t ) )
		
def createPlans ( psPlanUrl, restCount ):
	plans = getExcelData( excelFile, 'Plans' )
	
	''' Get Existing Plan Information '''
	psPlanOutput, t, status, statusText, restCount = getRest( psPlanUrl, session, payload, None, requestHeader, authorization, recordLimit, log, restCount)
	psPlanIdList, psPlanXref = getPsPlanId( psPlanOutput, log )	
		
	'''	For each plan that does not already exist, insert OrgId	'''
	for plan in plans:
		if plan['PlanName'] in ( [dict['PlanName'] for dict in psPlanIdList] ):
			log.info('\t\t**Plan %s already exists, skipping' % ( plan['PlanName'] ) )
		else:
			#plan.pop('PlanId')
			plan['OrganizationId'] = orgXref[ plan['OrganizationCode'] ]
			log.info('\tCreating Plan %s' % ( plan['PlanName'] ) )
			output, t, status, statusText, restCount = postRest( psPlanUrl, session, plan, requestHeader, authorization, log, restCount )
			
def segmentXreference ( orgs, segCodes, restCount ):
	segmentCodeIdXref ={}	
	for org in orgs:
		log.info('\t\t-->\tAttributeCode AttributeID Cross reference for %s ' % (segCodes))
		attrUrl = getUrl( psOrgUrl, str(orgXref[org]), 'child/attributes' )
		psOrgAttr, t, status, statusText, restCount = getRest( attrUrl, session, payload, None, requestHeader, authorization, recordLimit, log, restCount)
		for orgAttr in psOrgAttr['items']:
			#print(orgAttr, '\n\n')
			attrKeys = getKey( orgAttr['links'] )
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
			attributeValueXref[ (segment[0], segment[1], attrVal['AttributeValueCode'] ) ] = [ attrVal['AttributeValueId'], attrValKeys ] 
	
	return attributeValueXref
	
def updateAttributeBatch( restCount ):
	log.info('\tUpdating AttributeValue Colors')
	start = getTime()
	attributeValues = getExcelData( excelFile, 'AttributeValue' )
	segmentCodes = set( (dict['OrganizationCode'], dict['SegmentCode']) for dict in attributeValues )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in attributeValues )
	
	segmentXref = segmentXreference( uniqueOrgs, segmentCodes, restCount )
	attrValXref = attributeValXreference( segmentCodes, segmentXref, restCount )  
	
	partsList = []
	for av in attributeValues:
		log.info('\t\t-->Getting Attribute Colors for %s: %s' % (av['SegmentCode'], av['AttributeValueCode']))
		attrColor={}
		attrColor['OrganizationId'] = orgXref[ av['OrganizationCode'] ]
		attrColor['AttributeId'] = segmentXref[ av['SegmentCode'] ][0]
		attrColor['AttributeValueId'] = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][0]
		attrColor['Color'] = av['Color']
		attrValKey = attrValXref [ (av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode']) ][1]
		postAttrValueUrl = getUrl( '',psOrganizationsRoot, str(orgXref[ av['OrganizationCode']]), 'child/attributes', segmentXref[av['SegmentCode']][1], 'child/attributeValues', attrValKey)
		parts = getParts(str(attrValXref[(av['OrganizationCode'], av['SegmentCode'], av['AttributeValueCode'])][0]), getUrl( '',psOrganizationsRoot, str(orgXref[ av['OrganizationCode']]), 'child/attributes', segmentXref[av['SegmentCode']][1], 'child/attributeValues', attrValKey), 'update', attrColor)
		partsList.append(parts)
		

	log.info('\t\tUpdating %s Attribute Color Records in batches of %s' % (len(partsList), batchChunks))
	t, status, statusText, restCount = postBatchRest( url, session, partsList, int(batchChunks), authorization, log, restCount )
	TotalTime = getTime() - start
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
	#print ('xxx ' + wcUrl)
	mfgWorkCenters, t, status, statusText, restCount = getRest ( wcUrl, mfgsession, payload, None, mfgrequestHeader, mfgauthorization, recordLimit, log, restCount )
	#Assumes work center ID is the same across orgs, if not need to add org as key
	wcXref = idCode ( mfgWorkCenters, 'WorkCenterCode', 'WorkCenterId', log )


	resourceXref = {}
	for wc in workCenters:
		log.info('\t\t-->ResourceName ResourceID Cross reference for resources in %s' % (str(wc)))
		wcResourceUrl = getUrl( wcUrl, str(wcXref[wc]), 'child/WorkCenterResource' )
		#wcResourceUrl = getUrl( wcUrl, str(300100209046811), 'child/WorkCenterResource' )
		wcResource, t, status, statusText, restCount = getRest( wcResourceUrl, mfgsession, payload, None, mfgrequestHeader, mfgauthorization, recordLimit, log, restCount)
		for resource in wcResource['items']:
			resourceXref[ resource['ResourceName'] ] = resource['ResourceId']
	
	segmentXref = segmentXreference( uniqueOrgs, segmentCodes, restCount )
	attrValXref = attributeValXreference( segmentCodes, segmentXref, restCount ) 
	
	#changeoverId = int(time.mktime(datetime.datetime.now().timetuple())*100000)
	#changeoverSeq = changeoverId
	
	changeoverSeq=int(time.mktime(datetime.datetime.now().timetuple())*100000)
	#changeoverSeq = 10000
	
	partsList = []
	for co in changeOvers:
		parts = {}
		coPayload ={}
		coPayload['OrganizationId'] = orgXref[ co['OrganizationCode' ] ]
		#coPayload['ChangeoverId'] = changeoverId
		#coPayload['ChangeoverSequenceNumber'] = co['ChangeoverSequenceNumber' ]
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
	#print (statusText)
	log.info('\t\tChangeovers:: %s REST calls in %s\tsec' % (restCount, TotalTime))
	
def updateResourceGroups( restCount ):
	log.info('\tUpdating ResourceGroups')
	start = getTime()
	resourceGroups = getExcelData( excelFile, 'ResourceGroups' )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in resourceGroups )
	rgId = 1

	partsList = []
	for rg in resourceGroups:
		log.info('\t\t-->Getting Resource Groups' )
		rgPayload = {}
		rgPayload['OrganizationId'] = orgXref[ rg['OrganizationCode' ] ]
		rgPayload['GroupCode'] = rg['GroupCode' ]
		rgPayload['Description'] = rg['Description' ]
		parts = getParts(str(rgId), getUrl(psOrganizationsRoot, str(orgXref[rg['OrganizationCode']]), 'child/resourceGroups'), 'create', rgPayload) 
		partsList.append(parts)
		rgId += 1
		
	log.info('\t\tUpdating %s ResourceGroup Records in batches of %s' % (len(partsList), batchChunks))
	#t, status, statusText, restCount = postBatchRest( url, session, partsList, int(batchChunks), authorization, log, restCount )
	TotalTime = getTime() - start
	log.info('\t\tUpdated ResourceGroups %s REST calls in %s\tsec' % (restCount, TotalTime))
	
	return groupXreference(uniqueOrgs, restCount)
	
def groupXreference ( orgs, restCount ):
	groupIdXref ={}	
	for org in orgs:
		log.info('\t\t-->\tResourceGroup Cross reference for %s ' % (org))
		rgUrl = getUrl( psOrgUrl, str(orgXref[org]), 'child/resourceGroups' )
		psResGroups, t, status, statusText, restCount = getRest( rgUrl, session, payload, None, requestHeader, authorization, recordLimit, log, restCount)

		for resGroup in psResGroups['items']:
			#print (resGroup)
			groupIdXref[resGroup['GroupCode']] = [resGroup['OrganizationId'], resGroup['GroupId']]
		#print (groupIdXref)

	return groupIdXref

def updateGroupMembers( groupIdXref, restCount ):
	log.info('\tUpdating ResourceGroup Members')
	start = getTime()
	groupMembers = getExcelData( excelFile, 'ResourceGroupMembers' )
	uniqueOrgs = set( dict['OrganizationCode'] for dict in groupMembers )
	gmId = 1

	partsList = []
	for g in groupMembers:
		log.info('\t\t-->Getting Resource Groups Members' )
		print (g)
		gPayload = {}
		gPayload['OrganizationId'] = orgXref[ g['OrganizationCode' ] ]
		gPayload['GroupCode'] = g['GroupCode' ]
		gPayload['WorkCenterCode'] = g['WorkCenterCode' ]
		parts = getParts(str(gmId), getUrl(psOrganizationsRoot, str(orgXref[g['OrganizationCode']]), 'child/resourceGroups'), 'create', gPayload) 
		partsList.append(parts)
		gmId += 1
		
	log.info('\t\tUpdating %s ResourceGroup Records in batches of %s' % (len(partsList), batchChunks))
	#t, status, statusText, restCount = postBatchRest( url, session, partsList, int(batchChunks), authorization, log, restCount )
	TotalTime = getTime() - start
	log.info('\t\tUpdated ResourceGroups %s REST calls in %s\tsec' % (restCount, TotalTime))
	
	return groupXreference(uniqueOrgs, restCount)
	
def dxt ( restCount ):
	plans = getExcelData( excelFile, 'Plans' )
	dxtUrl ='https://fuscdrmsmc141-fa-ext.us.oracle.com/fscmRestApi/resources/11.13.18.05/productionSchedulingPlans/300100185100807/enclosure/EngineStateFile'
	''' Get Existing Plan Information '''
	psPlanOutput, t, status, statusText, restCount = getRest( dxtUrl, session, payload, None, requestHeader, authorization, None, log, restCount)
		
	print (psPlanOutput)

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
	
	#createPlans( psPlanUrl, restCount) 
	updateAttributeBatch( restCount )
	createChangeoversBatch (restCount)
	#dxt( restCount )
	#resourceGroups = updateResourceGroups(restCount)
	#print (resourceGroups)
	#updateGroupMembers(resourceGroups, restCount)
