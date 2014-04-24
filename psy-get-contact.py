#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# psy-get-contact.py v0.2
# By: psychedelys
# Email: psychedelys@googlemail.com
# https://github.com/psychedelys/cisco79xx_phone_directory
# Part of the cisco79xx_phone_directory stuff hosted on github.
# Purpose: extract google contact from severals accounts and generate an all-in-one csv file.
# Requirements: python, gdata python client.
#
# License:
#
# This Package is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this package; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# On Debian & Ubuntu systems, a complete copy of the GPL can be found under
# /usr/share/common-licenses/GPL-3, or (at your option) any later version

import re,sys,os
import unicodedata
import gdata.contacts.data
import gdata.contacts.client
import gdata.contacts.service
from xml.etree import ElementTree
import atom
import ConfigParser

# Encode your Personal exeption rules inside the following dicts

skip_pattern_label = {
  'old': r'old|obsolet|deprecated',
}

sub_pattern_label = {
}

skip_pattern_rel = {
}

sub_pattern_rel = {
  'dash': r'^.*#',
}

skip_pattern_text = {
  'notint': r'^[^(\+|00)]',
}

sub_pattern_text = {
  'non-digit': r'[^\d]+',
}

skip_pattern_title = {
}

sub_pattern_title = {
}

skip_cmd_label = {}
skip_cmd_rel = {}
skip_cmd_text = {}
skip_cmd_title = {}
for pat in skip_pattern_label:
  skip_cmd_label[pat] = re.compile(skip_pattern_label[pat], flags=re.I)

for pat in skip_pattern_rel:
  skip_cmd_rel[pat] = re.compile(skip_pattern_rel[pat], flags=re.I)

for pat in skip_pattern_text:
  skip_cmd_text[pat] = re.compile(skip_pattern_text[pat], flags=re.I)

for pat in skip_pattern_title:
  skip_cmd_title[pat] = re.compile(skip_pattern_title[pat], flags=re.I)

sub_cmd_label = {}
sub_cmd_rel = {}
sub_cmd_text = {}
sub_cmd_title = {}
for pat in sub_pattern_label:
  sub_cmd_label[pat] = re.compile(sub_pattern_label[pat])

for pat in sub_pattern_rel:
  sub_cmd_rel[pat] = re.compile(sub_pattern_rel[pat])

for pat in sub_pattern_text:
  sub_cmd_text[pat] = re.compile(sub_pattern_text[pat])

for pat in sub_pattern_title:
  sub_cmd_title[pat] = re.compile(sub_pattern_title[pat])

def remove_accents(str):
        """
        Thanks to MiniQuark:
        http://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string/517974#517974
        """

        nkfd_form = unicodedata.normalize('NFKD', unicode(str))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

def remove_accents_bis(str):
        """
        remove eszett char
        """
        return str.replace( 'ß','ss')


class ContactsSample(object):
  """ContactsSample object demonstrates operations with the Google Contacts feed."""

  def __init__(self, email, password, source):
    """Constructor for the ContactsSample object.
    
    Takes an email and password associated with a google mail account to
    demonstrate the functionality of the Contacts feed.
    
    Args:
      email: [string] The e-mail address of the account to use for the sample.
      password: [string] The password associated with the previously [email parameter] account specified.
      source: [string] The service (scripts) requesting the data.
    
    Yields:
      A ContactsSample object used to run the sample demonstrating the
      functionality of the Contacts feed.
    """
    self.gd_client = gdata.contacts.service.ContactsService()
    self.gd_client.ssl = True
    self.gd_client.email = email
    self.gd_client.password = password
    self.gd_client.source = source
    self.gd_client.ProgrammaticLogin()

    query = gdata.contacts.service.ContactsQuery()
    query.max_results = 1000
    self.feed = self.gd_client.GetContactsFeed(query.ToUri())


  def extract_to_dict(self, list):
        """Prints out the contents of a feed to the console.

        Args:
        feed: A gdata.contacts.ContactsFeed instance.

        Returns:
        The number of entries printed, including those previously printed as
        specified in ctr. This is for passing as an argument to ctr on
        successive calls to this method.

        """

        if not self.feed.entry:
           print '\nNo entries in feed.\n'
           return 0
        else:
           print '\n%d entries in feed.\n' % (len(self.feed.entry))

        for i, entry in enumerate(self.feed.entry):

          if entry.title.text is None:
            # print "ERROR - Could not get from Line: %s" % (entry.title.text)
            continue

          try:
            try:
               try:
                  entry.title.text=entry.title.text.decode('utf-8','ignore')
               except UnicodeDecodeError:
                  entry.title.text=entry.title.text.decode('iso8859_15','replace')
               except UnicodeEncodeError:
                  entry.title.text=entry.title.text.decode('iso8859_15','replace')
                     
            except UnicodeDecodeError:
               print entry.title.text
               print unicode(entry.title.text, 'utf-8')
               entry.title.text=entry.title.text.decode('cp437','replace')
            except UnicodeEncodeError:
               print entry.title.text
               print unicode(entry.title.text, 'utf-8')
               entry.title.text=entry.title.text.decode('cp437','replace')
   
          except UnicodeDecodeError:
            print "ERROR - Could not remove from Line: %s" % (entry.title.text)
            continue
          except UnicodeEncodeError:
            print "ERROR - Could not remove from Line: %s" % (entry.title.text)
            continue
   
          try:
            entry.title.text = remove_accents(entry.title.text)
            entry.title.text = remove_accents_bis(entry.title.text)
          except:
            print "ERROR - Could not remove accent from the data source from Line: %s" % (entry.title.text)
   
          entry.title.text = entry.title.text.title()

          skip = 0
          for regex in skip_cmd_title:
            if skip_cmd_title[regex].search( entry.title.text ):
              skip = 1
              break

          if skip == 1:
            continue

          # Phone number in the contacts
          for phone in entry.phone_number:

              # Skipping
              skip = 0
              if phone.label:
                for regex in skip_cmd_label:
                  if skip_cmd_label[regex].search( phone.label ):
                    skip = 1
                    break

              if phone.rel and skip == 0:
                for regex in skip_cmd_rel:
                  if skip_cmd_rel[regex].search( phone.rel ):
                    skip = 1
                    break

              if phone.text and skip == 0:
                for regex in skip_cmd_text:
                  if skip_cmd_text[regex].search( phone.text ):
                    skip = 1
                    break

              if skip == 1:
                continue

              # Clean-up
              if phone.label:
                for regex in sub_cmd_label:
                  phone.label = sub_cmd_label[regex].sub( '', phone.label)

              if phone.rel:
                for regex in sub_cmd_rel:
                  phone.rel = sub_cmd_rel[regex].sub( '', phone.rel)

              if phone.text:
                phone.text = re.sub(r'^\+', '00', phone.text)
                for regex in sub_cmd_text:
                  phone.text = sub_cmd_text[regex].sub('', phone.text)

              if phone.label is not None:
                phone.rel = phone.rel+'-'+phone.label

              # list entry is format
              listentry = str ( "%s;%s;%s" %(entry.title.text, phone.rel, phone.text) )  
              # print listentry

              # Check that the entry doesnot yet exist
              found = 0
              for x in list:
                 if x == listentry:
                    # print 'Duplicate of ' + x
                    found = 1  
                    break 

              # append the contact data preformated in the dictionary
              if found == 0:
                 list.append( listentry )
        return list

  def PrintDict_to_disk(self, dict):
        """Prints out the contents of a feed to the console.

        Args:
        dict: A python dictionary containing the data inside.

        Returns:
        Nothing, but generate a csv file 'contacts_extract.csv'.

        """

        if len(dict) == 0 :
                print '\nNo entries in final csv.\n'
                return 0
        else:
                print '\n%d entries in final csv.\n' % (len(dict))

        f = open('contacts_extract.csv', 'w')
        for i in dict:
            f.write( "%s\n" %(i) )
        f.close()


def main():

  reload(sys)
  sys.setdefaultencoding( "utf-8" )

  p = ConfigParser.ConfigParser()
  p.read("global.ini")

  sections = p.sections()
  dict = []

  for section in sections: 
    if p.get(section, 'enable') != '1':
      continue

    google_email = p.get(section, 'username')
    google_passwd = p.get(section, 'password') 
    google_source = 'psy-get-contact-0.1'

    try:
      contacts = ContactsSample(google_email, google_passwd, google_source)
    except gdata.service.BadAuthentication:
      print 'Invalid user credentials given.'
      return

    print "account: %s" % (google_email)

    dict = contacts.extract_to_dict(dict)

  contacts.PrintDict_to_disk(dict)


if __name__ == "__main__":
        main()
