# -*- coding: utf-8 -*-
'''
Copyright (C) 2012-2018  Diego Torres Milano
Created on Feb 2, 2015

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Diego Torres Milano
'''

__version__ = '15.4.0'

import json
import os
import platform
import re
import subprocess
import sys
import threading

try:
    import requests

    REQUESTS_AVAILABLE = True
except:
    REQUESTS_AVAILABLE = False
import time
from ..adb.adbclient import AdbClient
from ..common import obtainAdbPath

__author__ = 'diego'

DEBUG = False

lock = threading.Lock()


class RunTestsThread(threading.Thread):
    """
    Runs the instrumentation for the specified package in a new thread.
    """

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None, adbClient=None,
                 testClass=None, testRunner=None):
        threading.Thread.__init__(self, group=group, target=target, name=name, verbose=verbose)
        self.adbClient = adbClient
        self.testClass = testClass
        self.testRunner = testRunner
        self.pkg = re.sub('\.test$', '', self.testClass)

    def run(self):
        if DEBUG:
            print("RunTestsThread: Acquiring lock", file=sys.stderr)
        lock.acquire()
        if DEBUG:
            print("RunTestsThread: Lock acquired", file=sys.stderr)
        self.forceStop()
        time.sleep(3)
        if DEBUG:
            print("Starting test...", file=sys.stderr)
            print("RunTestsThread: Releasing lock", file=sys.stderr)
        lock.release()
        out = self.adbClient.shell('am instrument -w ' + self.testClass + '/' + self.testRunner + '; echo "ERROR: $?"')
        if DEBUG:
            print("\nFinished test.", file=sys.stderr)
        errmsg = out.splitlines()[-1]
        m = re.match('ERROR: (\d+)', errmsg)
        if m:
            exitval = int(m.group(1))
            if exitval != 0:
                raise RuntimeError('Cannot start test on device: ' + out)
        else:
            raise RuntimeError('Unknown message')

    def forceStop(self):
        if DEBUG:
            print("Cleaning up before start. Stopping '%s'" % self.pkg, file=sys.stderr)
        self.adbClient.shell('am force-stop ' + self.pkg)


class UiAutomatorHelper:
    PACKAGE = 'com.dtmilano.android.culebratester'
    TEST_CLASS = PACKAGE + '.test'
    TEST_RUNNER = 'com.dtmilano.android.uiautomatorhelper.UiAutomatorHelperTestRunner'

    def __init__(self, adbclient, adb=None, localport=9999, remoteport=9999, hostname='localhost'):
        if not REQUESTS_AVAILABLE:
            raise Exception('''Python Requests is needed for UiAutomatorHelper to work.

On Ubuntu install

   $ sudo apt-get install python-requests

On OSX install

   $ easy_install requests
''')

        self.adbClient = adbclient
        ''' The adb client (a.k.a. device) '''
        instrumentation = self.adbClient.shell('pm list instrumentation %s' % self.PACKAGE)
        if not instrumentation:
            raise RuntimeError('The target device does not contain the instrumentation for %s' % self.PACKAGE)
        if not re.match('instrumentation:%s/%s \(target=%s\)' % (self.TEST_CLASS, self.TEST_RUNNER, self.PACKAGE),
                        instrumentation):
            raise RuntimeError('The instrumentation found for %s does not match the expected %s/%s' % (
            self.PACKAGE, self.TEST_CLASS, self.TEST_RUNNER))
        self.adb = self.__whichAdb(adb)
        ''' The adb command '''
        self.osName = platform.system()
        ''' The OS name. We sometimes need specific behavior. '''
        self.isDarwin = (self.osName == 'Darwin')
        ''' Is it Mac OSX? '''
        self.hostname = hostname
        ''' The hostname we are connecting to. '''
        if hostname in ['localhost', '127.0.0.1']:
            self.__redirectPort(localport, remoteport)
        self.__runTests()
        self.baseUrl = 'http://%s:%d' % (hostname, localport)
        try:
            self.session = self.__connectSession()
        except RuntimeError as ex:
            self.thread.forceStop()
            raise ex

    def __connectSession(self):
        if DEBUG:
            print("UiAutomatorHelper: Acquiring lock", file=sys.stderr)
        lock.acquire()
        if DEBUG:
            print("UiAutomatorHelper: Lock acquired", file=sys.stderr)
            print("UiAutomatorHelper: Connecting session", file=sys.stderr)
        session = requests.Session()
        if not session:
            raise RuntimeError("Cannot create session")
        tries = 10
        while tries > 0:
            time.sleep(0.5)
            if DEBUG:
                print("UiAutomatorHelper: Attempting to connect to", self.baseUrl, '(tries=%s)' % tries, file=sys.stderr)
            try:
                response = session.head(self.baseUrl)
                if response.status_code == 200:
                    break
            except requests.exceptions.ConnectionError as ex:
                tries -= 1
        lock.release()
        if tries == 0:
            raise RuntimeError("Cannot connect to " + self.baseUrl)
        if DEBUG:
            print("UiAutomatorHelper: HEAD", response, file=sys.stderr)
            print("UiAutomatorHelper: Releasing lock", file=sys.stderr)
        # lock.release()
        return session

    def __whichAdb(self, adb):
        if adb:
            if not os.access(adb, os.X_OK):
                raise Exception('adb="%s" is not executable' % adb)
        else:
            # Using adbclient we don't need adb executable yet (maybe it's needed if we want to
            # start adb if not running) or to redirect ports
            adb = obtainAdbPath()

        return adb

    def __redirectPort(self, localport, remoteport):
        self.localPort = localport
        self.remotePort = remoteport
        subprocess.check_call([self.adb, '-s', self.adbClient.serialno, 'forward', 'tcp:%d' % self.localPort,
                               'tcp:%d' % self.remotePort])

    def __runTests(self):
        if DEBUG:
            print("__runTests: start", file=sys.stderr)
        # We need a new AdbClient instance with timeout=None (means, no timeout) for the long running test service
        newAdbClient = AdbClient(self.adbClient.serialno, self.adbClient.hostname, self.adbClient.port, timeout=None)
        self.thread = RunTestsThread(adbClient=newAdbClient, testClass=self.TEST_CLASS, testRunner=self.TEST_RUNNER)
        if DEBUG:
            print("__runTests: starting thread", file=sys.stderr)
        self.thread.start()
        if DEBUG:
            print("__runTests: end", file=sys.stderr)

    def __httpCommand(self, url, params=None, method='GET'):
        if method == 'GET':
            if params:
                response = self.session.get(self.baseUrl + url, params=params)
            else:
                response = self.session.get(self.baseUrl + url)
        elif method == 'PUT':
            response = self.session.put(self.baseUrl + url, params=params)
        else:
            raise RuntimeError("method not supported: " + method)
        return response.content

    #
    # Device
    #
    def getDisplayRealSize(self):
        return self.__httpCommand('/Device/getDisplayRealSize')

    #
    # UiAutomatorHelper internal commands
    #
    def quit(self):
        try:
            self.__httpCommand('/UiAutomatorHelper/quit')
        except:
            pass
        self.session.close()

    #
    # UiDevice
    #
    def click(self, **kwargs):
        params = kwargs
        if not (('x' in params and 'y' in params) or 'oid' in params):
            raise RuntimeError('click: (x, y) or oid must have a value')
        if 'oid' in params:
            return self.__httpCommand('/UiObject2/%d/click' % params['oid'])
        else:
            return self.__httpCommand('/UiDevice/click', params)

    def dumpWindowHierarchy(self):
        dump = self.__httpCommand('/UiDevice/dumpWindowHierarchy').decode(encoding='UTF-8', errors='replace')
        if DEBUG:
            print("DUMP: ", dump, file=sys.stderr)
        return dump

    def findObject(self, **kwargs):
        params = kwargs
        if not ('resourceId' in params or 'bySelector' in params):
            raise RuntimeError('findObject: resourceId or bySelector must have a value')
        response = self.__httpCommand('/UiDevice/findObject', params)
        # { "status": "OK", "oid": 1, "className": "android.view.View"}
        if DEBUG:
            print("UiAutomatorHelper: findObject: response=", response, file=sys.stderr)
        r = json.loads(response)
        if r['status'] == 'OK':
            if DEBUG:
                print("UiAutomatorHelper: findObject: returning", int(r['oid']), file=sys.stderr)
            return UiObject2(self, int(r['oid']))
        elif r['status'] == 'ERROR':
            if DEBUG:
                print("UiAutomatorHelper: findObject: returning", int(r['oid']), file=sys.stderr)
            if r['statusCode'] == -1:
                # Object not found
                return None
        raise RuntimeError("Error: " + response)

    def longClick(self, **kwargs):
        params = kwargs
        if not (('x' in params and 'y' in params) or 'oid' in params):
            raise RuntimeError('longClick: (x, y) or oid must have a value')
        if 'oid' in params:
            return self.__httpCommand('/UiObject2/%d/longClick' % params['oid'])
        else:
            return self.__httpCommand('/UiDevice/longClick', params)

    def openNotification(self):
        return self.__httpCommand('/UiDevice/openNotification')

    def openQuickSettings(self):
        return self.__httpCommand('/UiDevice/openQuickSettings')

    def pressBack(self):
        return self.__httpCommand('/UiDevice/pressBack')

    def pressHome(self):
        return self.__httpCommand('/UiDevice/pressHome')

    def pressKeyCode(self, keyCode, metaState=0):
        params = {'keyCode': keyCode, 'metaState': metaState}
        return self.__httpCommand('/UiDevice/pressKeyCode', params)

    def pressRecentApps(self):
        return self.__httpCommand('/UiDevice/pressRecentApps')

    def swipe(self, startX=-1, startY=-1, endX=-1, endY=-1, steps=10, segments=[], segmentSteps=5):
        if startX != -1 and startY != -1:
            params = {'startX': startX, 'startY': startY, 'endX': endX, 'endY': endY, 'steps': steps}
        elif segments:
            params = {'segments': ','.join(str(p) for p in segments), "segmentSteps": segmentSteps}
        else:
            raise RuntimeError(
                "Cannot determine method invocation from provided parameters. startX and startY or segments must be provided.")
        return self.__httpCommand('/UiDevice/swipe', params)

    def takeScreenshot(self, scale=1.0, quality=90):
        params = {'scale': scale, 'quality': quality}
        return self.__httpCommand('/UiDevice/takeScreenshot', params)

    def waitForIdle(self, timeout):
        params = {'timeout': timeout}
        return self.__httpCommand('/UiDevice/waitForIdle')

    #
    # UiObject
    #
    def setText(self, uiObject, text):
        # NOTICE: uiObject can receive UiObject or UiObject2
        element = uiObject.__class__.__name__
        _f = {'UiObject': '0x%x', 'UiObject2': '%d'}[element]
        params = {'text': text}
        return self.__httpCommand(('/%s/' + _f + '/setText') % (element, uiObject.oid), params)

    #
    # UiObject2
    #
    def clickAndWait(self, uiObject2, eventCondition, timeout):
        params = {'eventCondition': eventCondition, 'timeout': timeout}
        return self.__httpCommand('/UiObject2/%d/clickAndWait' % uiObject2.oid, params)

    def getText(self, uiObject=None):
        # NOTICE: uiObject can receive UiObject or UiObject2
        element = uiObject.__class__.__name__
        _f = {'UiObject': '0x%x', 'UiObject2': '%d'}[element]
        if uiObject:
            path = ('/%s/' + _f + '/getText') % (element, uiObject.oid)
        else:
            raise ValueError("No uiObject or uiObject2 specified")
        response = self.__httpCommand(path, None)
        r = json.loads(response)
        if r['status'] == 'OK':
            if DEBUG:
                print("UiAutomatorHelper: getText: returning", r['text'], file=sys.stderr)
            return r['text']
        raise RuntimeError("Error: " + response)

    def isChecked(self, uiObject=None):
        # This path works for UiObject and UiObject2, so there's no need to handle both cases differently
        path = '/UiObject/%d/isChecked' % (uiObject.oid)
        response = self.__httpCommand(path, None)
        r = json.loads(response)
        if r['status'] == 'OK':
            return r['checked']
        raise RuntimeError("Error: " + response)

    #
    # UiScrollable
    #
    def uiScrollable(self, path, params=None):
        response = self.__httpCommand('/UiScrollable/' + path, params)
        if DEBUG:
            print("UiAutomatorHelper: uiScrollable: response=", response, file=sys.stderr)
        r = None
        try:
            r = json.loads(response)
        except:
            print("====================================", file=sys.stderr)
            print("Invalid JSON RESPONSE: ", response, file=sys.stderr)
        if r['status'] == 'OK':
            if 'oid' in r:
                if DEBUG:
                    print("UiAutomatorHelper: uiScrollable: returning", int(r['oid']), file=sys.stderr)
                return int(r['oid']), r
            else:
                return r
        if DEBUG:
            print("RESPONSE: ", response, file=sys.stderr)
            print("r=", r, file=sys.stderr)
        raise RuntimeError("Error: " + response)


class UiObject:
    def __init__(self, uiAutomatorHelper, oid, response):
        self.uiAutomatorHelper = uiAutomatorHelper
        self.oid = oid
        self.className = response['className']

    def getOid(self):
        return self.oid

    def getClassName(self):
        return self.className

    def click(self):
        self.uiAutomatorHelper.click(oid=self.oid)

    def longClick(self):
        self.uiAutomatorHelper.longClick(oid=self.oid)

    def getText(self):
        return self.uiAutomatorHelper.getText(uiObject=self)

    def setText(self, text):
        self.uiAutomatorHelper.setText(uiObject=self, text=text)


class UiObject2:
    def __init__(self, uiAutomatorHelper, oid):
        self.uiAutomatorHelper = uiAutomatorHelper
        self.oid = oid

    def click(self):
        self.uiAutomatorHelper.click(oid=self.oid)

    def clickAndWait(self, eventCondition, timeout):
        self.uiAutomatorHelper.clickAndWait(uiObject2=self, eventCondition=eventCondition, timeout=timeout)

    def isChecked(self):
        """

        :rtype: bool
        """
        return self.uiAutomatorHelper.isChecked(uiObject=self)

    def longClick(self):
        self.uiAutomatorHelper.longClick(oid=self.oid)

    def getText(self):
        # NOTICE: even if this is an uiObject2 we are invoking the only "getText" method in UiAutomatorHelper
        # passing the uiObject2 as uiObject
        return self.uiAutomatorHelper.getText(uiObject=self)

    def setText(self, text):
        # NOTICE: even if this is an uiObject2 we are invoking the only "setText" method in UiAutomatorHelper
        # passing the uiObject2 as uiObject
        self.uiAutomatorHelper.setText(uiObject=self, text=text)


class UiScrollable:
    def __init__(self, uiAutomatorHelper, uiSelector):
        self.uiAutomatorHelper = uiAutomatorHelper
        self.uiSelector = uiSelector
        self.oid, self.response = self.__createUiScrollable()

    def __createUiScrollable(self):
        return self.uiAutomatorHelper.uiScrollable('new', {'uiSelector': self.uiSelector})

    def flingBackward(self):
        return self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/flingBackward')

    def flingForward(self):
        return self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/flingForward')

    def flingToBeginning(self, maxSwipes=20):
        return self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/flingToBeginning', {'maxSwipes': maxSwipes})

    def flingToEnd(self, maxSwipes=20):
        return self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/flingToEnd', {'maxSwipes': maxSwipes})

    def getChildByDescription(self, uiSelector, description, allowScrollSearch):
        oid, response = self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/getChildByDescription',
                                                            {'uiSelector': uiSelector,
                                                             'contentDescription': description,
                                                             'allowScrollSearch': allowScrollSearch})
        return UiObject(self.uiAutomatorHelper, oid, response)

    def getChildByText(self, uiSelector, text, allowScrollSearch):
        oid, response = self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/getChildByText',
                                                            {'uiSelector': uiSelector, 'text': text,
                                                             'allowScrollSearch': allowScrollSearch})
        return UiObject(self.uiAutomatorHelper, oid, response)

    def setAsHorizontalList(self):
        self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/setAsHorizontalList')
        return self

    def setAsVerticalList(self):
        self.uiAutomatorHelper.uiScrollable(str(self.oid) + '/setAsVerticalList')
        return self
