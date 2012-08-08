[IVRHub](https://ivrhub.org) is a mobile data collection system built by [Aquaya](http://aquaya.org).
Surveys are created in a web interface and responses are completed via a phone call.
Respondents may speak their answers or use their phone's keypad to reply.
This is a hosted service that requires no on-the-ground hardware installations.
Respondents can use simple phones to fill out surveys - no special apps are required.
We built IVRHub to test phone-based data collection in several different countries.
This is a great tool for prototyping and quickly gauging the feasibility of an IVR-based solution.
For projects that can support hardware on the ground and require thousands of respondents
we recommend looking at telephony platforms like [FreedomFone](http://www.freedomfone.org).


### Use Cases
Data collection for water plant operators

1. Project manager sets up a survey and schedule
2. The survey consists of several spoken questions regarding O&M activities
3. Every Friday at 4pm, personnel receive a short phone call playing back the
manager's voice questions and recording their answers
4. The manager may view the raw responses on the web interface
or in [Pipeline](https://github.com/aquaya/pipeline)

Data collection for mobile staff

1. Auditors check up on rural water supplies
2. After testing a water source, the auditors call in to IVRHub and select a "blank" form
3. Their responses are visible on the site for further analysis


### Requirements
Tested on Ubuntu 11.10.

You'll need a locally-running mongodb instance - see their docs for more info.

use `virtualenv` and `pip` to install other requirements:

    $ virtualenv /path/to/venv
    $ pip install -r requirements.txt -E /path/to/venv

after cloning this repo, pull in the dependencies:
    
    $ git submodule init
    $ git submodule update


### Third party services
If you are running this service you'll need accounts with Twilio and AWS.


### Running locally
setup a real config file outside of source control

    $ cp conf/ivrhub_settings_sample.py /path/to/real/settings.py              

edit that new config..then point an env var at it

    $ export IVRHUB_SETTINGS=/path/to/real/settings.py

activate your virtualenv and create the default admin

    $ ./path/to/venv/bin/activate
    (venv)$ python
    >> import ivrhub 
    >> ivrhub.views.seed()

start up the server

    (venv)$ python run.py
    * Running on http://127.0.0.1:8000/


### Usage in production
we have some example config files for supervisord, gunicorn, nginx, and fabric -- check those out

Bootstrapping a new server:
 
 - install virtualenv and pip
 - copy over config files for supervisord, gunicorn, nginx and this app
 - make a dir for the config files and the log files
 - point the env var to the app config file and put this in your .zshrc
 - use fabric to install the app 
 - reload/reread/restart supervisord until it picks up the config file (annoyingly imprecise, I know..)
 - start the server and check with supervisorctl
 - edit the nginx config file at nginx.conf and the sites-availble dir (symlink to sites-enabled); restart nginx
 - seed the db from a shell
 - update your DNS 
