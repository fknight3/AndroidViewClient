AndroidViewClient for Python ≥3.6
=================

**This is a Python 3.6 compatible fork of the original [_dtmilano's_ AndroidViewClient](https://github.com/dtmilano/AndroidViewClient) repository.**

#### Why ≥3.6 instead of ≥ 3?
I share my opinion with _Kenneth Reitz's_ (quoted on [The Hitchhiker's Guide to Python](http://docs.python-guide.org/en/latest/starting/which-python/#recommendations)) and believe that Python 3 is the future. Moreover, Python versions 3.5 and 3.6 added many useful features to the language which I like and use frequently.

I try to keep my code as PEP compatible, organized and clean as possible - thanks to [PyCharm](https://www.jetbrains.com/pycharm/) IDE for making all of this possible while making my life easier.

##

<a href="#"><img src="https://github.com/dtmilano/AndroidViewClient/wiki/images/culebra-logo-transparent-204x209-rb-border.png" align="left" hspace="0" vspace="6"></a>
**AndroidViewClient** was originally conceived as an extension to [monkeyrunner](http://developer.android.com/tools/help/monkeyrunner_concepts.html) but lately evolved
as a pure python tool that automates or simplifies test script creation.
It is a test framework for Android applications that:
<ul><ul>
    <li>Automates driving Android applications</li>
    <li><b>Generates</b> re-usable scripts</li>
    <li>Provides view-based <i>device independent</i> UI interaction</li>
    <li>Uses 'logical' screen comparison (UI Automator Hierarchy based) over image comparison (Avoiding extraneous 
    detail issues, such as time or data changes)</li>
    <li>Supports running on multiple devices</li>
    <li>Provides simple control for high level operations like language change and activity start</li>
    <li>Supports all Android APIs</li>
    <li>Is written in python</li>
</ul></ul>

[![Latest Version](https://img.shields.io/pypi/v/androidviewclient.svg)](https://pypi.python.org/pypi/androidviewclient/)


:rage: **NOTE**: Pypi statistics are broken see [here](https://github.com/aclark4life/vanity/issues/22). The new statistics can be obtained from [BigQuery](https://bigquery.cloud.google.com/queries/culebra-tester).

As of June 2018 we have reached:

<img src="https://github.com/dtmilano/AndroidViewClient/wiki/images/culebra-400k.png" width="80%" align="center">

Thanks to all who made it possible.

# Want to learn more?
Detailed information can be found in the [AndroidViewClient/culebra wiki](https://github.com/dtmilano/AndroidViewClient/wiki)

