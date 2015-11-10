#!/usr/bin/python
usage = "launch_autosummary.py [--options]"
description = "a wrapper around autosummary.py to set it up and run under lvalert_listen. WARNING: our neighbors logic is not fool-proof if we specify different windows for each event_type, which is currently allowed."
auther = "Reed Essick (reed.essick@ligo.org)"

import sys
import json

import subprocess as sp

from ConfigParser import SafeConfigParser
from optparse import OptionParser

#=================================================

parser = OptionParser(usage=usage, description=description)

parser.add_option("-v", "--verbose", default=False, action="store_true")

parser.add_option("-c", "--config", default="./config.ini", type="string")

parser.add_option("-l", "--log-dir", defualt=".", type="string")

parser.add_option("", "--dont-wait", default=False, action="store_true", help="do not wait for one GraceID to complete before launching neighbors")

opts, args = parser.parse_args()

#=================================================

### read lvalert 
alert = sys.stdin.read()

if opts.verbose:
    print "alert received:\n%s"%alert

alert = json.loads(alert)

### determine if we need to react (only when there is a new FITS file)
if (alert['alert_type'] == 'update') and alert['filename'].strip(".gz").endswidth(".fits"):  ### check for new FITS file 

    ### configure command
    if opts.verbose:
        print "new FITS file : %s -> %s"%(alert['uid'], alert['filename'])
        print "reading config : %s"%(opts.config)
    config = SafeConfigParser()
    config.read( opts.config )

    ### figure out which event_type this is
    if config.has_option( "general", "gracedb_url" ):
        gracedb = GraceDb( config.get("general", "gracedb_url") )
    else:
        gracedb = GraceDb()

    gid_todo = [ alert['uid'] ]
    gid_done = []

    while len(gid_todo):
        gid = pop( gid_todo )
        if opts.verbose:
            print "working on : %s"%gid

        event = gracedb.event( gid ).json()
        if event.has_key( 'search' ):
            event_type = "%s_%s_%s"%(evnet['group'], event['pipeline'], event['search'])
        else:
            event_type = "%s_%s"%(event['group'], event['pipeline'])
        event_type = event_type.lower()
    
        ### get options for autosummary
        options = dict( config.items( "general" ) )
        if config.has_section( event_type ):
            if opts.verbose:
                print "\tloading extra instructions from section : %s"%event_type
            options.update( dict( config.items( event_type ) ) )
        elif verbose:
            print "\tno section found for event_type : %s"%event_type

        if options.has_key("neighbors-window"):
            w = float(options["neighbors-window"])
            if w > 0:
                ### find neighbors
                neighbors = [e for e in gracedb.events( "%.6f .. %.6f"%(event['gps']-w, event['gps']+w) ) if (e['graceid'][0] != "H") and (e['graceid'] != gid)]

                ### filter neighbors
                if options.has_key('neighbors-not-my-group'):
                    neighbors = [e for e in neighbors if (e['group'] != event['group'])]
                elif options.has_key('neighbors-not-my-pipeline'):
                    neighbors = [e for e in neighbors if (e['pipeline'] != event['pipeline'])]
                elif options.has_key('neighbors-not-my-search') and event.has_key('search'):
                    neighbors = [e for e in neighbors if (not e.has_key('search')) or (e['search']==event['search'])]

                ### add neighbors if they are not already scheduled
                for e in neighbors:
                    if e['graceid'] not in gid_todo+gid_done:
                        gid_todo.append( e['graceid'] )

        cmd = "autosummary.py %s %s"%( gid, " ".join("--%s %s"%tup for tup in options) )
        out = "%s/autosummary_%s.out"%(opts.log_dir, gid)
        err = "%s.err"%(out[:-4])

        ### launch
        if opts.verbose:
            print "%s > %s, %s"%(cmd, out, err)
        out_obj = open(out, "w")
        err_obj = open(err, "w")
#        proc = sp.Popen( cmd.split(), stdout=out_obj, stderr=err_obj )
#        if opts.verbose:
#            print "process successfully forked : %s -> %d"%(gid, proc.pid)
        out_obj.close()
        err_obj.close()

#        if not opts.dont_wait:
#            proc.wait()

        gid_done.append( gid )

elif opts.verobse:
    print "alert isn't about a new FITS file, ignoring"
