import sys, os
import json
import urllib.parse
from oraRESTTools import *
import datetime
import time

def getPlan(url, restCount):
	planOutput, t, status, statusText, restCount = getRest( url, session, payload, requestHeader, authorization, recordLimit, log, restCount)
	planIdList, planXref = getPsPlanId( planOutput, log )

	return planIdList, planXref, restCount

def runSteps(steps, plansXref, endPoint, statusField, restCount, log):
	for s in steps:
		start = getTime()
		log.info('\tProcessing Step: %s' % (s['Step']))
		time.sleep(5)
		if s['Body']:
			body = json.loads(s['Body'])
		else:
			body = getPsBody(s['Action'], s['Parameters'])
		planUrl = getUrl( url, endPoint, str(plansXref[s['PlanName']]), 'child/Runs')	
		#planUrl = getUrl( url, endPoint, str(plansXref[s['PlanName']]))	#For SOP
		t, status, statusText, restCount = postRest( planUrl, session, body, requestHeader, authorization, log, restCount )
		if status == 200 or status == 201:
			processStatus = None
			while processStatus == None or processStatus == 1:  #For SOP
			#while processStatus == None or processStatus == 0:
				time.sleep(10)
				psStatus, t, status, statusText, restCount = getRest( planUrl, session, payload, requestHeader, authorization, None, log, restCount)
				processStatus = psStatus[statusField]
				t = getTime() - start
				log.info('\t\t\t%s\t\tWaiting....' % (t))
			log.info('\t\tCOMPLETED')
		else:
			log.info('\tERROR:\t\n%s' % (statusText))
			#print (statusText)

if __name__ == "__main__":
	'''	Set Variables, logging, and establish Session 	'''
	log = setLogging()
	variables = setVariables('psRest.xml')
	for key,val in variables.items():
		exec(key + '=val')	
		
	session, authorization, requestHeader, payload = scmAuth ( user, password )
	log.info('REST Server: %s' % ( url ))
	restCount = 0
	
	''' 	PS Plan Steps 	'''
	#0: processing, 1: completed, 2: error


	#psUrl = getUrl( url, rootResource)
	#psPlanIdList, psPlanXref, restCount = getPlan( psUrl, restCount)
	#psActions = getExcelData( excelFile, 'Process' )

	#runSteps(psActions, psPlanXref,'productionSchedulingPlans', 'LastRequestStatus', restCount, log)

	
	''' 	SOP Plan Steps 	'''
	#0: completed, 1: processing, 2: error, or 3: warning

	url = 'https://fuscdrmsmc326-fa-ext.us.oracle.com/fscmRestApi/resources/11.13.18.05'
	scpUrl = getUrl(url, 'supplyChainPlans')
	scpPlanIdList, scpPlanXref, restCount = getPlan(scpUrl, restCount)
	scpActions = getExcelData( excelFile, 'scpProcess' )
	runSteps(scpActions, scpPlanXref, 'salesAndOperationsPlans','PlanStatus', restCount, log)
	#print (scpPlanXref['AK-REST'])
	#print (scpPlanIdList, len(scpPlanIdList))
