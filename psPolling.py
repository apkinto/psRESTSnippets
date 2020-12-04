import sys, os
import json
import urllib.parse
from oraRESTTools import *
import datetime
import time

def getPlan(url, restCount):
	log.info('\tGetting Plans...')
	planOutput, t, status, statusText, restCount = getRest( url, session, payload, None, requestHeader, authorization, recordLimit, log, restCount)
	log.info('\tRetrieved Plans in %s seconds...' % (t))
	planIdList, planXref = getPsPlanId( planOutput, log )

	return planIdList, planXref, restCount
	
def pollEss(essJobId, interval, restCount):
	postUrl = getUrl( url, 'erpintegrations')
	
	essBody = {}
	essBody['OperationName'] = 'getESSJobStatus'
	essBody['ReqstId'] = essJobId
	essStatus=None
	
	requestHeader['Content-Type'] = 'application/json'
	while essStatus not in ["ERROR", "SUCCEEDED"]:
		essOutput, t, status, statusText, restCount = postRest( postUrl, session, essBody, requestHeader, authorization, log, restCount )
		essStatus = essOutput['RequestStatus']
		log.info('\t\t...ESS JobId: %s --> %s' % (essJobId, essStatus))
		time.sleep(interval)
	else:
		log.info('\tFinished with status %s' % (essStatus))
	
	return essStatus

def runSteps(steps, plansXref, statusField, statusCodes, scpAction, restCount, interval, log):
	for s in steps:
		start = getTime()
		log.info('\tProcessing Step: %s' % (s['Step']))

		# If the Excel worksheet contains this field, it is used to run SCP processes else PS processes which uses the Action field
		if s['Body']:				
			body = json.loads(s['Body'])
		else:
			body = getPsBody(s['Action'], s['Parameters'])

		if s['Type'] == 'collections':
			postUrl = getUrl( url, 'dataCollections')
			essJobField = 'ESSCollectionJobId'
		else:
			postUrl = getUrl( url, s['Type'], str(plansXref[s['PlanName']]), scpAction)
			#essJobField = 'JobId'
			essJobField = 'result'
		
		requestHeader['Content-Type'] = 'application/vnd.oracle.adf.action+json'
		output, t, status, statusText, restCount = postRest( postUrl, session, body, requestHeader, authorization, log, restCount )
		essJobId = getEssJobId(output, essJobField)
		
		if status == 200 or status == 201:
			pollEss(essJobId, interval, restCount)
		else:
			log.info('\tERROR:\t\n%s' % (statusText))	

if __name__ == "__main__":
	'''	Set Variables, logging, and establish Session 	'''
	log = setLogging()
	variables = setVariables('poll.xml')
	for key,val in variables.items():
		exec(key + '=val')	
		
	session, authorization, requestHeader, payload = scmAuth ( user, password )
	log.info('REST Server: %s' % ( url ))
	restCount = 0
	
	''' 	PS Plan Steps 	'''
	#0: processing, 1: completed, 2: error
	
	psUrl = getUrl( url, 'productionSchedulingPlans')
	psPlanIdList, psPlanXref, restCount = getPlan( psUrl, restCount)
	psActions = getExcelData( excelFile, 'Process' )

	runSteps(psActions, psPlanXref, 'LastRequestStatus', [1], None, restCount, int(interval), log)

	


	
	