import sys, os
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
	orgXref = idCode ( psOrganizations, 'Organization', log )
	#print ( orgXref )
	#for org in orgXref.items():
	#	print ( org )
	
	''' Get Existing Plan Information '''
	psPlanOutput, t, status = getRest( psPlanUrl, session, payload, requestHeader, authorization, recordLimit, log )
	psPlanIdList = getPsPlanId( psPlanOutput, log )	
	#print ( psPlanIdList ) 
	
	'''  Read data from excel worksheet '''
	plans = readExcel( excelData, 'Plans' )
	
	'''	For each plan, insert OrgId	'''
	for plan in plans:
		plan.pop('PlanId')
		plan['OrganizationId'] = orgXref[ plan['OrganizationCode'] ]
	#print ( plans )
	
	postData( plans, psPlanUrl )
	
	