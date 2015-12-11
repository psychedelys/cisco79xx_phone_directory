#!/usr/bin/env python

#   Gigaset entreprise phone directory: a Flask app to use 
#   a csv contacts file as the phone directory for the Siemens
#   Gigaset N510 IP PRO basis.
#
#   Copyright (C) 2014-2015 Psychedelys <psychedelys@gmail.com>
#   http://github.com/psychedelys/cisco79xx_phone_directory
#
#   Based on the cisco script of the same repository and
#   https://teamwork.gigaset.com/gigawiki/display/GPPPO/Online+directory
#   1.04.02.pub.2.public_pbs_protocol_spec.pdf
#
#   Implementation is not complete at all, this is more a poc.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import unicodedata
from flask import Flask, request
from xml.etree import ElementTree
import csv
import sys

# CONFIGURATION REQUIRED:
CONTACTS_FILE = "contacts_extract.csv"

app = Flask(__name__)

class DirectoryEntry:
    """
    Contains the phone number, owner's name and the label associated
    to the phone number.
    """
    def __init__(self, number, name, label):
        # Discard non-digit characters
        self.number = number
        self.name = name
        self.label = label

    def __str__(self):
        if self.label:
            return "%s (%s)" % (self.name, self.label,)
        else:
            return self.name

def get_directory():
    """
    Parses the CSV Contacts file and returns its contents as a list
    of DirectoryEntry instances.
    """
    print "parsing file %s" % CONTACTS_FILE 
    directory = []

    for line in csv.reader(open(CONTACTS_FILE), delimiter=';', skipinitialspace=True):
        directory.append(DirectoryEntry(line[2],line[0],line[1]))

    return directory

def generate_directory_xml(directory,offset,params):
    """
    Generates the XML required to display the phone directory from
    the list of DirectoryEntry instances given as a parameter.
    """

    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    max = len(directory)
    # print >> sys.stderr, "in max with '%s' vs. '%s'" % (max, params['count'])
    if max > params['count']:
       max = params['count']
    # print >> sys.stderr, "in max with '%s' vs. '%s'" % (max, params['count'])
    xml += "<list response=\"%s\" type=\"%s\" reqid=\"%s\" total=\"%s\" first=\"%s\" last=\"%s\" >\n" % ( params['command'], params['type'], params['reqid'], max, params['first'], max )
    id=1
    for entry in directory:
        if id > max:
           break
        xml += "\t<entry id=\"%i\">\n" % id
        xml += "\t<ln>%s</ln>\n" % entry
        if entry.label == "mobile":
          # print >> sys.stderr, "XML mb:%s,%s,%s" % (id,entry,entry.number)
          xml += "\t<mb>%s</mb>\n" % entry.number
        elif entry.label == "work":
          # print >> sys.stderr, "XML w:%s,%s,%s" % (id,entry,entry.number)
          xml += "\t<hm>%s</hm>\n" % entry.number
        elif entry.label == "home":
          # print >> sys.stderr, "XML hm:%s,%s,%s" % (id,entry,entry.number)
          xml += "\t<hm>%s</hm>\n" % entry.number
        else:
          # print >> sys.stderr, "XML hm:%s,%s,%s" % (id,entry,entry.number)
          xml += "\t<hm>%s</hm>\n" % entry.number
        xml += "\t</entry>\n"
        id = id + 1

    xml += "</list>\n"
    return xml

@app.route("/phonebook.xml")
def index():
    """
    Serves the phone directory search page and the search results.
    """
    
    notfound = 'ct' 

    # wildcard: %2a

    parameters = {}

    if "command" in request.args:
        parameters['command'] = request.args["command"]
    else:
        parameters['command'] = "get_list"

    # Phone Book
    # The type identifies which type of list shall be retrieved from the server
    # * pb: list of public phonebook entries
    # * yp: list of yellow pages entries
    # * pr: list of private phonebook entries 
    if "type" in request.args:
        parameters['type'] = request.args["type"]
    else:
        parameters['type'] = 'pr'

    # reqid: (optional)
    # is a hexadecimal string with a maximum length of 32 characters. It identifies
    # unambiguously a list that is addressed by the request. The identifier is set by the server for
    # identification of a list. Within the first request from client the reqid tag is empty or omitted.
    # All subsequent requests to the list, due to several pages in the list, are addressed by the
    # same reqid given by the server in the first request. 
    if "reqid" in request.args:
        parameters['reqid'] = request.args["reqid"]
    else:
        # todo random...
        parameters['reqid'] = '29AF5'

    # first:
    # is the first item in a request. This tag is used if the request is asked for item n till n+count-1.
    # Note: If the tag "first" is used, a following tag "last" is not allowed.
    # * first=1: for the first request of a list the item should begin by 1.
    # * first>0: for subsequent request beginning from a defined offset of items for a forward search request.
    if "first" in request.args:
        parameters['first'] = request.args["first"]
        notfound = 'first'

    # last:
    # is the last item in a request. This tag is used if the request is asked for item n till
    # n-count+1. Nevertheless the items are sorted in ascending order. If the tag last is used, a
    # following tag "first" is not allowed. In this case error id 2 (syntax error) will be returned from
    # server.
    # * last>0: item number for which the request starts backwards
    # * last=-1: request starts from last item in the whole list backwards
    if "last" in request.args:
        parameters['last'] = request.args["last"]
        notfound = 'last'

    # count:
    # is the maximum amount of items which are requested from the server.
    # * count>0: amount of items to return to the client. If the overall size of
    # data exceeds the "limit" the returned amount of items are shortened at
    # the "far end" (i.e. opposite the specified first/last). Only complete items
    # are sent.
    if "count" in request.args:
        parameters['count'] = int(request.args["count"])

    # limit:
    # The limit defines the maximum amount of memory that the client is able to process for
    # each server response. This includes all the data which will be returned by the server
    # (Header and payload).
    # * limit>=1024 amount of data in bytes
    # TODO: not implemented...
    if "limit" in request.args:
        parameters['limit'] = request.args["limit"]

    # reqsrc: (optional)
    # Request source is a flag that indicate who starts phonebook search:
    # * auto: auto lookup (search is started for number lookup service)
    # * user: manual search performed by user hands
    # If this parameter is missing, and server supports it, server should assume "user"
    # request source.

    offset = 0

    xml = '<?xml version="1.0" encoding="UTF-8"?><list response="%s" type="%s" reqid="%s" notfound="%s" total="0"/>' % (parameters['command'], parameters['type'], parameters['reqid'], notfound )

    # We have received the query string, display the results
    # nickname
    if "nn" in request.args and request.args["nn"] != '*':
        keyword = request.args["nn"]
        # print >> sys.stderr, "in nn with '%s'" % (keyword)
        keyword = keyword.replace('*','')
        # print >> sys.stderr, "in nn with '%s'" % (keyword)
        # Get the directory and filter the entries based on the keyword, then sort them
        directory = sorted([entry for entry in get_directory() if keyword.lower() in unicode(entry.name).lower() or keyword in unicode(entry.number)], key=lambda entry: unicode(entry))
        xml = generate_directory_xml(directory,offset,parameters)

    # Firstname
    elif "fn" in request.args and request.args["fn"] != '*':
        keyword = request.args["fn"]
        # print >> sys.stderr, "in fn with '%s'" % (keyword)
        keyword = keyword.replace('*','')
        # print >> sys.stderr, "in fn with '%s'" % (keyword)
        # Get the directory and filter the entries based on the keyword, then sort them
        directory = sorted([entry for entry in get_directory() if keyword.lower() in unicode(entry.name).lower() or keyword in unicode(entry.number)], key=lambda entry: unicode(entry))
        xml = generate_directory_xml(directory,offset,parameters)

    # Lastname
    elif "ln" in request.args and request.args["ln"] != '*':
        keyword = request.args["ln"]
        # print >> sys.stderr, "in ln with '%s'" % (keyword)
        keyword = keyword.replace('*','')
        # print >> sys.stderr, "in ln with '%s'" % (keyword)
        # Get the directory and filter the entries based on the keyword, then sort them
        directory = sorted([entry for entry in get_directory() if keyword.lower() in unicode(entry.name).lower() or keyword in unicode(entry.number)], key=lambda entry: unicode(entry))
        xml = generate_directory_xml(directory,offset,parameters)


    # home phone number
    elif "hm" in request.args and request.args["hm"] != '*':
        phone = request.args["hm"]
        # print >> sys.stderr, "in hm with '%s'" % (phone)
        phone = phone.replace('*','')
        # print >> sys.stderr, "in hm with '%s'" % (phone)
        # Get the directory and filter the entries based on the phone, then sort them
        directory = sorted([entry for entry in get_directory() if phone.lower() in unicode(entry.name).lower() or phone in unicode(entry.number)], key=lambda entry: unicode(entry))
        xml = generate_directory_xml(directory,offset,parameters)

    # mobile phone number
    elif "mb" in request.args and request.args["mb"] != '*':
        phone = request.args["mb"]
        # print >> sys.stderr, "in mb with '%s'" % (phone)
        phone = phone.replace('*','')
        # print >> sys.stderr, "in mb with '%s'" % (phone)
        # Get the directory and filter the entries based on the phone, then sort them
        directory = sorted([entry for entry in get_directory() if phone.lower() in unicode(entry.name).lower() or phone in unicode(entry.number)], key=lambda entry: unicode(entry))
        xml = generate_directory_xml(directory,offset,parameters)

#    else:
#        # generate a fake answers...
#        phone = request.args["hm"]
#        print >> sys.stderr, "in hm with '%s'" % (phone)
#        phone = phone.replace('*','')
#        print >> sys.stderr, "in hm with '%s'" % (phone)
#        directory = sorted([entry for entry in get_directory() if phone.lower() in unicode(entry.name).lower() or phone in unicode(entry.number)], key=lambda entry: unicode(entry))
#        xml = generate_directory_xml(directory,offset,parameters)

    response = app.response_class(xml, mimetype='text/xml')

    return response


if __name__ == "__main__":
    """
    Starts the debug webserver if the script is called from the command-line.
    WARNING: The debug webserver uses HTTP/1.0 by default, which is not
    supported by the Gigaset N510 according to docs. Reverse-proxy are nice. 
    Have a look at the README file if you haven't already!
    """
    app.run(debug=True,port=5100)

