#!/usr/bin/env python

#   Cisco 79xx phone directory: a Flask app to use Google Contacts
#   as the phone directory for the Cisco 79xx IP phones.
#   Copyright (C) 2010-2011 Francois Lebel <francoislebel@gmail.com>
#   http://github.com/flebel/cisco79xx_phone_directory
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

# CONFIGURATION REQUIRED:
# Change these to fit your needs, the port has to match the one on
# which the webserver listens to. It is required to hardcode the port
# number in order to work around a bug with the Cisco 79xx browser.
CONTACTS_FILE = "contacts_extract.csv"
PORT = 5006
HOST = "192.168.178.20"
DIRECTORY_URL = "http://%s:%d/directory.xml" % (HOST, PORT)

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
    Parses the Google Contacts file and returns its contents as a list
    of DirectoryEntry instances.
    """
    print "parsing file %s" % CONTACTS_FILE 
    directory = []

    for line in csv.reader(open(CONTACTS_FILE), delimiter=';', skipinitialspace=True):
        # print "added: '%s' '%s' '%s'" % (line[2],line[0],line[1])
        # directory.append(DirectoryEntry(number, name, label))
        directory.append(DirectoryEntry(line[2],line[0],line[1]))

    return directory


def generate_directory_xml(directory,offset,maxEntry):
    """
    Generates the XML required to display the phone directory from
    the list of DirectoryEntry instances given as a parameter.
    """
    # Todo: generate the next page with offset
    xml = "<CiscoIPPhoneDirectory>\n"
    xml += "\t<Title>Phone directory</Title>\n"
    xml += "\t<Prompt>Select an entry.</Prompt>\n"
    for entry in directory:
        xml += "\t<DirectoryEntry>\n"
        xml += "\t\t<Name>%s</Name>\n" % entry
        xml += "\t\t<Telephone>%s</Telephone>\n" % entry.number
        xml += "\t</DirectoryEntry>\n"
    xml += "</CiscoIPPhoneDirectory>\n"
    return xml


def generate_search_xml():
    """
    Generates the XML required to display a phone directory search
    page on the Cisco 79xx IP phones.
    """
    xml = "<CiscoIPPhoneInput>\n"
    xml += "\t<Title>Search for an entry</Title>\n"
    xml += "\t<Prompt>Enter a search keyword.</Prompt>\n"
    # For a reason unbeknown to me, the Cisco 7940 IP phone is the only
    # device/browser for which the request.environ["SERVER_PORT"] value is
    # set to 80 although the URL accessed is on another port, therefore
    # forcing us to use a hardcoded port number
    # xml += "\t<URL>http://%s:%d/directory.xml</URL>\n" % (request.environ["SERVER_NAME"], PORT,)
    xml += "\t<URL>%s</URL>\n" % (DIRECTORY_URL)
    xml += "\t<InputItem>\n"
    xml += "\t\t<DisplayName>Keyword</DisplayName>\n"
    xml += "\t\t<QueryStringParam>keyword</QueryStringParam>\n"
    xml += "\t\t<InputFlags></InputFlags>\n"
    xml += "\t\t<DefaultValue></DefaultValue>\n"
    xml += "\t</InputItem>\n"
    xml += "</CiscoIPPhoneInput>\n"
    return xml


@app.route("/directory.xml")
def index():
    """
    Serves the phone directory search page and the search results.
    """

    if "offset" in request.args:
        offset = request.args["offset"]
    else:
        offset = 0
    maxEntry = offset + 32
    myentry = 0

    # We have received the query string, display the results
    if "keyword" in request.args:
        keyword = request.args["keyword"]
        # Get the directory and filter the entries based on the keyword, then sort them
        directory = sorted([entry for entry in get_directory() if keyword.lower() in unicode(entry.name).lower() or keyword in unicode(entry.number)], key=lambda entry: unicode(entry))
        xml = generate_directory_xml(directory,offset,maxEntry)
    # If we haven't received the query string, display the search menu
    else:
        xml = generate_search_xml()
    response = app.response_class(xml, mimetype='text/xml')
    # response.headers['X-offset'] = 'parachutes are cool'
    if myentry == 32:
       response.headers['Refresh'] = 0
       response.headers['url'] = "%s?offset=maxEntry" % ( DIRECTORY_URL )

    return response


if __name__ == "__main__":
    """
    Starts the debug webserver if the script is called from the command-line.
    WARNING: The debug webserver uses HTTP/1.0 by default, which is not
    supported by the Cisco 79xx IP phones. Have a look at the README file
    if you haven't already!
    """
    app.run(debug=False,port=5000)

