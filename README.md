# psRESTUtilities
REST Samples/Examples.  Note, these are not intended to be used in a production environment and are examples only as it does not contain robust exception handling.  There is no support for using this.   Google is a greate resource.  

Utilities that may be handy when using REST for Oracle SaaS applications

#GETTING STARTED
Requires Python 3.7.x
Requires xlrd for reading .xls and .xlsx files

Download psRest.xml, oraRESTTools.py to a directory
Change parameters in psRest.xml.  Parameters can be added in the XML and will be available in the script (see example in psPostData.py)

Note, although .xlsx can be used .xls is used in general but only required when converting background colors to a Hex RGB value since the xlrd library only supports this with .xls

psData.xls and psPostData.py are examples of using these utilities

Log is created in the input directory.

