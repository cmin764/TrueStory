# TrueStory

*Be your own journalist.*

Web platform and API gathering and exposing similar but opposed news articles. This
lives into Google Cloud Platform, but works and can be tested locally too.


## Installation

#### Set up Google Cloud environment and tools:

Make sure you have Python 2 installed and active in the system.

1. Follow the steps here: https://cloud.google.com/sdk/
2. Install App Engine tools:
```bash
$ gcloud components install app-engine-python app-engine-python-extras cloud-datastore-emulator beta
$ gcloud components update  # from time to time
```

#### Install Python 3 interpreter and pip:

```bash
$ brew update && brew install python3
$ easy_install-3.7 --upgrade pip
$ pip3 --version  # pip 19... ...(python 3.7)
```

#### Clone repository and run server:

```bash
$ git clone https://github.com/savvybit/TrueStory.git
$ cd TrueStory
```

Before running it, in order to not have any conflicts with the `gcloud` suite, it's
recommended to play with the project in a virtual environment. Make sure you follow the
instructions [here](https://github.com/pyenv/pyenv) and also configure your *.bashrc*,
*.bash_profile* or *.profile* accordingly.

```bash
$ brew install pyenv pyenv-virtualenv pyenv-virtualenvwrapper
$ pyenv virtualenv -p python3.7 truestory  # creates a 3.7 venv named 'truestory'
$ pyenv local truestory  # sets it as default venv for this project
```

Now don't forget to configure the above virtual environment in your favorite IDE too
(as default interpreter).

Finally, run the Flask app:

```bash
$ ./run.sh
```


#### Test if everything works correctly:

Before running them, make sure you have all the requirements installed and a Datastore
emulator open (if you want to run DB related tests too, otherwise they'll be skipped).

```bash
$ pyenv shell system  # emulator can't be opened under venv (gcloud requires system's Python 2)
$ ./research/ops/datastore-emulator.sh  # opens an emulator in detached state
```

And now in another tab (for having *truestory* venv active):

```bash
$ pip install -Ur requirements-test.txt  # these should be already installed by the previous `./run.sh` 
$ ./test.sh
```


## Usage

#### Run CLI and explore various commands:

```bash
$ truestory --help
```

Crawl and save articles into the *development* remote database.

```bash
$ truestory -v crawl -s
```

Put a `-h` after each command in order to see detailed info about it and what it does.


## Deployment

Simply run `./deploy.sh` script (outside virtualenv, by running `pyenv shell system`
first) with any of the *develop* or *master* parameters (representing the version of
GAE).

#### Notes

- Everything deployed into *master* will automatically be promoted, meaning that the
  entire traffic will be redirected in this version.
- Deployments under *develop* are not promoted, but they are accessible through URLs
  like https://develop-dot-truestory.appspot.com.
- Tests are using the **testing** namespace no matter if the remote or emulated
  Datastore is used.
- Local server will automatically have DEBUG mode activated and use the **development**
  Flask config, settings and Datastore namespace (so look for entities there if you're
  exploring the remote online Datastore console).  
- If you're asked for any credentials (using remote Datastore, development or
  production), don't forget to make them available like this:
  ```bash
  $ export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials/TrueStory-83153701f337.json"
  ```
  *Ask Cosmin for the JSON file and keep it private.*

----

* Source: https://github.com/savvybit/TrueStory.git
* License: MIT
* Authors:
    + Cosmin Poieana \<cmin764@gmail.com\>
    + Irina Bejan \<irinam.bejan@gmail.com\>
