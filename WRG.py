#!/usr/bin/env python2

username = ""
password = ""
target   = ""
email    = ""

import cPickle as pickle
import os
import subprocess
import time
import whatapi

class WhatRequestGrab(object):

    SCRIPT_DIR  = os.path.dirname(os.path.realpath(sys.argv[0]))
    STATE_FILE  = os.path.join(SCRIPT_DIR, 'wrg.dat')

    timeformat = "%Y-%m-%d %H:%M:%S"

    def __init__(self, state_file=None):

        self.state_file  = state_file or WhatRequestGrab.STATE_FILE

        self.first_run = False
        try:
            self.state = pickle.load(open(self.state_file, 'rb'))
        except:
            self.first_run = True
            self.state = {}

        self.last_filled = self.state.get('last_filled', "1901-01-01 00:00:00")
        self.last_filled = time.strptime(self.last_filled, WhatRequestGrab.timeformat)

        cookies = self.state.get('cookies')
        self.what = whatapi.WhatAPI(username=username, password=password, cookies=cookies)
        self.state['cookies'] = self.what.session.cookies
        self.save_state()

        self.filled_requests = []

    def run(self):
        self.find_requests()
        self.send_notifications()

    def find_requests(self):
        page = 1

        while True:

            data = self.what.request("requests", **{'type': "voted", 'order': "filled", 'page': page})

            for request in data['response']['results']:
                if request['isFilled']:
                    time_filled = time.strptime(request['timeFilled'], WhatRequestGrab.timeformat)
                    if time_filled > self.last_filled:
                        self.filled_requests.append(request)
                    else:
                        return

            if data['response']['currentPage'] == data['response']['pages']:
                break
            else:
                page += 1

    def save_state(self):
        pickle.dump(self.state, open(datfile, 'wb'))

    def send_notifications(self):
        if self.first_run:
            # Record current state only.
            self.state['last_filled'] = self.filled_requests[0]['timeFilled']
            self.save_state()
            return

        home_dir = os.path.expanduser("~")
        base_url = "https://what.cd/torrents.php?action=download&id=%s&authkey=%s&torrent_pass=%s"

        for request in reversed(self.filled_requests):
            if request['artists']:
                message = "Request Filled: %s - %s [%s]" % (request['artists'][0][0]['name'], request['title'], request['formatList'])
            else:
                message = "Request Filled: %s" % (request['title'])
            subprocess.Popen(["mailx", email], cwd=home_dir, stdin=subprocess.PIPE).communicate(message.encode("utf-8"))

            torrent_url = base_url % (request['torrentId'], self.what.authkey, self.what.passkey)
            subprocess.Popen(["wget", "--quiet", "--content-disposition", torrent_url], cwd=target)

            self.state['last_filled'] = request['timeFilled']
            self.save_state()

WhatRequestGrab().run()
