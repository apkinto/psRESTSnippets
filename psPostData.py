import sys, os
from psRestUtilities import *


def postData ( ):
		
	b =[{"PlanName": "AK-REST1","OrganizationId": 209, "HorizonDuration": 30,    "HorizonDurationUnit": "days",	"AnchorTimestamp": "2018-12-24T08:00:00+00:00",   "HorizonAnchorBehavior": "Rolling",    "HorizonStartDate": "2018-12-27T19:46:58-08:00",    "HorizonEndDate": "2019-01-31T19:47:07-08:00",    "CalendarHorizonStartDate": "2018-01-20T19:47:20-08:00",    "CalendarHorizonEndDate": "2019-07-30T19:47:47-07:00",    "DataHorizonStartDate": "2018-01-20T19:48:47-08:00",    "DataHorizonEndDate": "2019-03-28T19:48:58-07:00",    "WorkOrderUnitOfEffort": "No","SolveTimeLimitDuration": 30,    "SolveTimeLimitUnit": "minutes"	}]
	
	for c in b:
		t, status, statusText = postRest( psPlanUrl, session, c, requestHeader, authorization, log )
		log.info('\tPOST StatusCode: %s\t Time: \t%s sec \t%s' % ( status, t, statusText ) )
	

if __name__ == "__main__":
	
	log = setLogging()
	variables = setVariables('psRest.xml')
	outDir = variables['psOutputDirectory']
	inputDir = variables['psInputDirectory']
	resourceList = variables['resourceList']
	rootResource = variables['rootResource']
	recordLimit = variables['recordLimit']
	url = variables['url']
	planId = variables['planId']
	resFile = os.path.join(inputDir, resourceList)	
	resources = getResources( resFile )
	username = variables['user']
	password = variables['password']
	
	session, authorization, requestHeader, payload = scmAuth ( username, password )
	
	log.info('REST Server: %s' % ( url ))
	psPlanUrl = getUrl( url, rootResource)
	
	#etData( recordLimit )
	postData()

	