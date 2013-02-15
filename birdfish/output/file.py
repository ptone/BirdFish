#!/usr/bin/env python

import csv
import time
import os

class EventWriter(object):
    def __init__(self, file=None):
        super(EventWriter, self).__init__()
        if not file:
            raise ValueError("no file path provided")
        if os.path.exists(file):
            raise ValueError("File Already Exists")
            # @@ could increment filename instead
        self.file = file
        self.writer = csv.writer(open(file, 'wb'))


    def log_event(self,object,type,data,attr=None, timing=None):
        if timing is None:
            timing = time.time()
        if object.name == "":
            raise ValueError("Unamed object can not be recorded")
        print object.name, type
        if attr:
            label = "%s.%s" % (object.name, attr)
        else:
            label = object.name
        self.writer.writerow([type, label, data, timing])
