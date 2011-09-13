#!/usr/bin/python
#
# Python frontend for editing ACDP hours with your favorite editor
# (discovered from VISUAL env)
#
# Copyright, (C) Eugeni Dodonov <eugeni@dodonov.net>, 2010
#
# Distributed under GPLv2 licence.
#
# vim:expandtab:shiftwidth=4:ts=4:smarttab:
#

import urllib,urllib2
import re
import tempfile
import sys
import os
import difflib
import time

CONFIGFILE = os.environ.get("ACDP_CONF", os.path.expanduser("~/.acdp"))

# regexps
# login failure
login_failure=re.compile('.*Login Failed. Please try again.*')
# person_id
person_id_r = re.compile('name="person_id" value="(\d+)"')
# person_name
person_name_r = re.compile('name="person_name" value="(.*)"></center>Internal Hours')
# month listing
list_entry = re.compile('<tr class="row1">\n\s*<td align="center">(\d+)</td>\n\s*<td align="left">(.*)</td>\n\s*<td align="center">(\d+)</td>\n\s*<td align="left"></td>\n\s*<td align="left">(.*)</td>')
# project listing
project_entry = re.compile('\?proj_id=(\d+)">(.*)</a>')
# editable entry
pyacdp_entry = re.compile('([+-]) (\d+)\s*(\d+)\s*(\d+)\s*(.*)')
# hours added
hours_added = re.compile('Your hours were added successfully')
# hours failure
hours_failure = re.compile('<span class="errormini">(.*)</span>')
# hours_modify_template
hours_modify_t = '<td align="left">%(project)s</td>\\n\\s*<td align="left">%(hours)s</td>\\n\\s*<td align="left">%(descr)s</td>\\n\\s*<td align="right"><form method="post" action="horas_projeto.php\?action=updatehrs&hours_id=(\\d+)"><input type="submit" name="updatehrs" value="Update"></form></td>'


DEFAULT_HOST = os.environ.get("ACDP_URL", "https://acdp.mandriva.com.br/")

DEBUG = os.environ.get("ACDP_DEBUG", False) and True

class ACDP:
    def __init__(self, host=DEFAULT_HOST):
        self.host = host
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        urllib2.install_opener(self.opener)
        self.projects_cache = {}
        self.projects_rev_cache = {}
        self.person_id = None
        self.person_name = None

    def login(self, login, passwd):
        """Login"""
        # TODO: person_id, person_name
        url = self.host + 'login.php'
        params = urllib.urlencode({
            'action': 'login',
            'GoAheadAndLogIn': 'Login',
            'user': login,
            'passwd': passwd
            })
        con = self.opener.open(url, params)
        res = con.read()
        failure = login_failure.findall(res)
        if DEBUG:
            print res
            print failure
        if len(failure) == 0:
            print "Logged in"
            return True
        else:
            print "NOT logged in"
            return False


    def list_hours(self, year, month):
        """Lists acdp hours"""
        url = self.host + 'relatorio.php?action=personal_month&year=%(year)d&month=%(month)d' % ({'year': year, 'month': month})
        params = urllib.urlencode({
            'detailed': '1'
            })
        con = self.opener.open(url, params)
        res = con.read()
        if DEBUG:
            print res
        hours = list_entry.findall(res)
        return hours

    def list_recent(self):
        """Lists recent projects"""
        url = self.host + 'horas_projeto.php?action=add'
        con = self.opener.open(url)
        res = con.read()
        res_nl = res.replace('<p>','\n<p>')
        if DEBUG:
            print res_nl
        projects = project_entry.findall(res_nl)
        person_id = person_id_r.findall(res_nl)
        if person_id:
            self.person_id = person_id[0]
        else:
            print "Error: person_id not found"
            return []
        person_name = person_name_r.findall(res_nl)
        if person_name:
            self.person_name = person_name[0]
        else:
            print "Error: person_name not found"
            return []
        for id, project in projects:
            self.projects_cache[project] = id
            self.projects_rev_cache[id] = project
        return projects


    def remove(self, proj, year, month, day, hours, descr):
        """Remove an entry"""
        print 'Removing "%s" (%s hours on %s) from %s: ' % (descr, hours, day, acdp.projects_rev_cache.get(proj, proj)),
        if not self.person_id or not self.person_name:
            print "Error: unable to add hours, unknown person_id or person_name"
            return False
        # fix day size
        if len(day) == 1:
            day = '0%s' % day
        month = str(month)
        if len(month) == 1:
            month = '0%s' % month

        # first lets get the hours id
        url = self.host + "relatorio.php?action=day&person_id=%s&report_day=%s&report_month=%s&report_year=%s" % (self.person_id, day, month, year)
        con = self.opener.open(url)
        res = con.read()
        hours_modify_c = hours_modify_t % ({'descr': descr, 'hours': hours, 'project': self.projects_rev_cache[proj]})
        if DEBUG:
            print hours_modify_c
        hours_modify_r = re.compile(hours_modify_c)
        hours_id_match = hours_modify_r.findall(res)
        if len(hours_id_match) > 0:
            hours_id = hours_id_match[0]
        else:
            print " Unable to determine hours_id, please delete the item manually"

        print "hours_id: %s " % hours_id,

        # let the fun begin
        url = self.host + 'horas_projeto.php?proj_id=%s' % proj
        params = urllib.urlencode({
            'action': 'remove',
            'hours_id': hours_id,
            })
        con = self.opener.open(url, params)
        res = con.read()
        print "done"
        pass

    def add(self, proj, year, month, day, hours, descr):
        """Add an entry"""
        print 'Adding "%s" (%s hours on %s) to %s: ' % (descr, hours, day, acdp.projects_rev_cache.get(proj, proj)),
        if not self.person_id or not self.person_name:
            print "Error: unable to add hours, unknown person_id or person_name"
            return False
        # fix day size
        if len(day) == 1:
            day = '0%s' % day
        month = str(month)
        if len(month) == 1:
            month = '0%s' % month
        url = self.host + 'horas_projeto.php?proj_id=%s' % proj
        params = urllib.urlencode({
            'find_single': '1',
            'action': 'add',
            'first_action': 'add',
            'do_action': '1',
            'person_id': self.person_id,
            'person_name': self.person_name,
            'horas': hours,
            'hours_desc': descr,
            'date_day': day,
            'date_month': month,
            'date_year': year,
            'detailed': '1'
            })
        con = self.opener.open(url, params)
        res = con.read()
        success = hours_added.findall(res)
        if success:
            print 'success'
            return True
        else:
            error = hours_failure.findall(res)
            if error:
                error_msg = error[0]
            else:
                error_msg = 'no details'
            tmp_in, tmp_name = tempfile.mkstemp(prefix='acdp_failure')
            fd = open(tmp_name, 'w')
            fd.write(res)
            fd.close()
            print 'failure (%s), full output available in %s' % (error_msg, tmp_name)
            return False
        pass


def leave(name_in, name_out, retcode=0):
    """Cleanups temporary files"""
    os.unlink(name_in)
    os.unlink(name_out)
    sys.exit(retcode)

if __name__ == "__main__":
    acdp = ACDP()
    fd_in, name_in = tempfile.mkstemp(suffix='acdp')
    fd_in = open(name_in, "w")
    fd_out, name_out = tempfile.mkstemp(suffix='acdp')
    fd_out = open(name_out, "w")
    login = None
    passwd = None

    if len(sys.argv) < 3:
        print "Usage: %s <month> <year>" % sys.argv[0]
        leave(name_in, name_out, 1)

    month = int(sys.argv[1])
    year = int(sys.argv[2])

    try:
        print "Trying to load authentication settings from %s" % CONFIGFILE
        if not os.path.exists(CONFIGFILE):
            print "Not found."
            import getpass
            login = raw_input("My Mandriva account: ")
            passwd = getpass.getpass()
        else:
            fd = open(CONFIGFILE, "r")
            login = fd.readline().strip()
            passwd = fd.readline().strip()
            fd.close()
    except:
        print "Error: please create %s, containing my.mandriva login on first line\nand password on 2nd" % CONFIGFILE
        leave(name_in, name_out, 1)

    # login
    if not acdp.login(login, passwd):
        print "Unable to login."
        leave(name_in, name_out, 1)
    recent_projects = acdp.list_recent()
    hours = acdp.list_hours(year, month)

    print >>fd_in, "# acdp data for %s / %s" % (month, year)
    print >>fd_in, "# cache of recent projects:"
    projects = {}
    for id, project in recent_projects:
        print >>fd_in, "# %s - %s" % (id, project)
        projects[project] = []
    print >> fd_in

    for day, project, hours, descr in hours:
        if project not in projects:
            projects[project] = []
        projects[project].append((day, hours, descr))

    for project in projects:
        print >>fd_in, "# %s" % project
        print >>fd_in, "# %pid\tday\thours\tdescription"
        for day, hours, descr in projects[project]:
            pid = acdp.projects_cache.get(project, '-1')
            print >>fd_in, "%s\t%s\t%s\t%s" % (pid, day, hours, descr)
        print >>fd_in

    # generate diffable files
    fd_in.close()
    with open(name_in, "r") as fd_in:
        data_in = fd_in.read()
    fd_out.write(data_in)
    fd_out.close()

    # edit output file
    editor = os.getenv("VISUAL", os.getenv("EDITOR"))
    if not editor:
        print "Error: VISUAL not defined, don't know what editor to use"
        leave(name_in, name_out, 1)

    if os.system("%s %s" % (editor, name_in)) != 0:
        print "Unable to edit file, aborting."
        leave(name_in, name_out, 1)

    # calculate diff
    fromdate = time.ctime(os.stat(name_out).st_mtime)
    todate = time.ctime(os.stat(name_in).st_mtime)
    fromlines = open(name_out, "U").readlines()
    tolines = open(name_in, "U").readlines()

    diff = "\n".join(difflib.ndiff(fromlines, tolines))
    changes = pyacdp_entry.findall(diff)

    for op, proj, day, hours, descr in changes:
        if op == '-':
            print 'Removing "%s" (%s hours on %s) from %s' % (descr, hours, day, acdp.projects_rev_cache.get(proj, proj))
        elif op == '+':
            print 'Adding "%s" (%s hours on %s) to %s' % (descr, hours, day, acdp.projects_rev_cache.get(proj, proj))

    print "Press ENTER to confirm or CTRL-C to abort.."
    try:
        res = raw_input()
    except KeyboardInterrupt:
        leave(name_in, name_out)

    # action
    for op, proj, day, hours, descr in changes:
        if op == '-':
            acdp.remove(proj, year, month, day, hours, descr)
        elif op == '+':
            acdp.add(proj, year, month, day, hours, descr)
    leave(name_in, name_out)
