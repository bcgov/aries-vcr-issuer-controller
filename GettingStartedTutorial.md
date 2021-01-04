# Aries VCR Getting Started Tutorial

This Getting Started Guide is to get someone new to the Aries VCR Issuer Controller get an agent up and running in about an hour.  We assume that if you are here, you have some background in the goals and purpose of Verifiable Credentials, Aries VCR, OrgBook and Aries VCR Issuer Agents.  If any of this is new to you, please learn more at [https://vonx.io](https://vonx.io). On that site, we recommend the overview in the "About" section, and especially, the webinar linked at the top.

## Table of Contents <!-- omit in toc -->

- [Aries VCR Getting Started Tutorial](#aries-vcr-getting-started-tutorial)
  - [Running in your Browser or on Local Machine](#running-in-your-browser-or-on-local-machine)
  - [Prerequisites](#prerequisites)
    - [In Browser](#in-browser)
    - [Local Machine](#local-machine)
  - [VON Network Setup](#von-network-setup)
    - [In Browser](#in-browser-1)
    - [Local Machine](#local-machine-1)
      - [VON Network](#von-network)
      - [Aries VCR](#aries-vcr)
  - [Step 1: Investigating VON](#step-1-investigating-von)
  - [Step 2: Getting Your VON Issuer/Verifier Agent Running](#step-2-getting-your-von-issuerverifier-agent-running)
    - [In Browser](#in-browser-2)
    - [Local Machine](#local-machine-2)
    - [Clone, Initialize and Start Your Agent](#clone-initialize-and-start-your-agent)
    - [Submit Credentials via API](#submit-credentials-via-api)
      - [Submit Credentials via Bulk Load Script](#submit-credentials-via-bulk-load-script)

## Running in your Browser or on Local Machine

This guide can be run from within a browser, or if you are more technically inclined, you can run it on your local machine using Docker. In the following sections, there are sub-sections for `In Browser` and `Local Machine`, depending on how you want to run the guide. If you are planning on setting up a new VON Issuer/Verifier Agent instance for your organization, we suggest you use the `Local Machine` path.

## Prerequisites

### In Browser

The only prerequisite (other than a browser) is an account with [Docker Hub](https://hub.docker.com). Docker Hub is the "Play Store" for the [Docker](https://docker.com) ecosystem.

### Local Machine

To run this guide on your local machine, you must have the following installed:

* Docker (Community Edition is fine)
  * If you do not already have Docker installed, go to [the Docker installation page](https://docs.docker.com/install/#supported-platforms) and click the link for your platform.
* Docker Compose
  * Instructions for installing docker-compose on a variety of platforms can be found [here](https://docs.docker.com/compose/install/).
* git
  * [This link](https://www.linode.com/docs/development/version-control/how-to-install-git-on-linux-mac-and-windows/) provides installation instructions for Mac, Linux (including if you are running Linux using VirtualBox) and native Windows (without VirtualBox).
* a bash shell
  * bash is the default shell for Mac and Linux.
  * On Windows, the git-bash version of the bash shell is installed with git and it works well. You **must** use bash to run the guide (PowerShell or Cmd will not work).
* curl
  * An optional step in the guide uses the utility `curl`.
  * curl is included on Mac and Linux.
  * Instructions for installing curl on Windows can be found [here](https://stackoverflow.com/questions/9507353/how-do-i-install-and-use-curl-on-windows).

## VON Network Setup

### In Browser

Go to [Play with Docker](https://labs.play-with-docker.com/) and (if necessary) click the login button. *Play With Docker* is operated by Docker to support developers learning to use Docker.

> If you want to learn more about the `Play with Docker` environment, look at the [About](https://training.play-with-docker.com/about/) and the Docker related tutorials at the Docker Labs [Training Site](https://training.play-with-docker.com). It's all great stuff created by the Docker Community. Kudos!

Click the `Start` button to start a Docker sandbox you can use to run the demo, and then click `+Add an Instance` to start a terminal in your browser. You have an instance of a Linux container running and have a bash command line.  We won't need to use the command line until Step 2 of this tutorial.

From time to time in the steps in this guide, we'll ask you to edit files. There are two ways to do that in this environment:

- If you are comfortable with the `vi` editor, you can just use that. If you don't know `vi`, don't try it. It's a little scary.
- Alternatively, there is an `Editor` button near the top of the screen. Click that and you get a list of files in your home directory, and clicking a file will open it in an editor.  You will probably need to expand the editor window to see the file. Make the changes in the editor and click the `Save` button.
  - Don't forget to click the `Save` button.

The following URLs are used in the steps below for the different components:

- The `von-network` URL - [http://greenlight.bcovrin.vonx.io](http://greenlight.bcovrin.vonx.io). You'll see a ledger browser UI showing four nodes up and running (blue circles).
- The `Aries VCR` URL  - [https://demo.orgbook.gov.bc.ca](https://demo.orgbook.gov.bc.ca) - You'll see the OrgBook interface with companies/credentials already loaded.

You can open those sites now or later. They'll be referenced by name (e.g. "The von-network URL...") in the guide steps.

### Local Machine

On a local machine upon which the prerequisites are setup, we will be installing and starting instances of [von-network](https://github.com/bcgov/von-network), and [Aries VCR](https://github.com/bcgov/aries-vcr).

#### VON Network

In a shell, run the following commands to start von-network:

```bash
git clone https://github.com/bcgov/von-network
cd von-network
./manage build
./manage start
```

After about 20 seconds or so, go to [http://localhost:9000](http://localhost:9000) in your browser and you should see a web page with the status of your network showing four nodes up and running (blue circles). If you don't get the server up immediately, wait longer and refresh your browser.  If you have a atypical docker and hosts setup, you may have to determine how to navigate to the correct page.

If you want to see the logs for von-network (especially if things aren't working), run from the same folder the command `./manage logs`. When you are done with the logs and you want to get back to the command line, type `Ctrl-c`.

When you are finished with the demo and want to stop the running von-network, run from the same folder the command `./manage stop`.

#### Aries VCR

After von-network has started, go to a second shell and run the following commands to start Aries VCR:

```bash
git clone https://github.com/bcgov/aries-vcr
cd aries-vcr/docker
./manage build
./manage start
```

The build step will take a long time to run, so sit back and relax...

Once you have run the `start` step and the logs look good, navigate to [http://localhost:8080](http://localhost:8080) in your browser to get to the Aries VCR home page. Sadly, you won't be able to do much because no credentials have been loaded, but at least everything is running!

When you are finished playing with the instance of Aries VCR, go back to your shell, hit Ctrl-c to get back to the command line prompt and run `./manage stop`. That will stop all of the running containers and clean up the volumes created as part of the Aries VCR instance.

## Step 1: Investigating VON

If you are new to VON, see the instructions in the respective repos for how to use the running instances of [von-network](https://github.com/bcgov/von-network) and [Aries VCR](https://github.com/bcgov/aries-vcr).

Our goal in this guide is to configure a new permit and/or licence VON issuer/verifier agent so that the credential will be discoverable in the Aries VCR instance.

## Step 2: Getting Your VON Issuer/Verifier Agent Running

In this step, we'll get an instance of your new VON issuer/verifier agent running and issuing credentials.

### In Browser

Start in the root folder of your Docker instance&mdash;where you began.

### Local Machine

Use a different shell from the one used to start the other components. After opening the new shell, start in the folder where you normally put the clones of your GitHub repos.

### Clone, Initialize and Start Your Agent

Clone the repo, and run the initialization script.

```bash
# Start in the folder with repos (Local Machine) or home directory (In Browser)
git clone https://github.com/bcgov/aries-vcr-issuer-controller
cd aries-vcr-issuer-controller
. init.sh  # And follow the prompts

```

The `init.sh` script does a number of things:

- Prompts for some names to use for your basic agent.
- Prompts for whether you are running with Play With Docker or locally and sets some variables accordingly.
- Registers a DID for you on the ledger that you are using.
- Shows you the lines that were changed in the agent configuration files (in [issuer_controller/config](issuer_controller/config)).

The initial agent you  created issues one credential, using the name you gave it, with a handful of claims: permit ID, permit type, etc. That credential depends on the applying organization already having the BC Registries "Registration" credential. Without already having that credential, an applying organization won't be able to get your agent's credential.

To start your agent, run through these steps:

```
cd docker   # Assumes you were already in the root of the cloned repo
./manage build
./manage start
```

After the last command, you will see a stream of logging commands as the agent starts up. The logging should stabilize with a "Completed sync: indy" entry.

When you need to get back to the command line, you can press `CTRL-c` to stop the stream of log commands. Pressing `CTRL-c` does not stop the containers running, it just stops the log from displaying. If you want to get back to seeing the log, you can run the command `./manage logs` from the `aries-vcr-issuer-controller/docker` folder.

To verify your agent is running:

1. Go to the `agent URL`, where you should see a "404" (not found) error message. That signals the agent is running, but does not respond to that route.
   1. For `In Browser`, click the "5001" link at the top of the screen. That's the path to your agent.
   2. For `Local Machine`, go to [http://localhost:5001](http://localhost:5001)

All good?  Whoohoo!

### Submit Credentials via API

To submit credentials, use Postman (or similar, based on your local configuration) to submit the following to http://localhost:5000/issue-credential

```
[
    {
        "schema": "ian-registration.ian-ville",
        "version": "1.0.0",
        "attributes": {
            "corp_num": "ABC12345",
            "registration_date": "2018-01-01", 
            "entity_name": "Ima Permit",
            "entity_name_effective": "2018-01-01", 
            "entity_status": "ACT", 
            "entity_status_effective": "2019-01-01",
            "entity_type": "ABC", 
            "registered_jurisdiction": "BC", 
            "addressee": "A Person",
            "address_line_1": "123 Some Street",
            "city": "Victoria",
            "country": "Canada",
            "postal_code": "V1V1V1",
            "province": "BC",
            "effective_date": "2019-01-01",
            "expiry_date": ""
        }
    },
    {
        "schema": "ian-permit.ian-ville",
        "version": "1.0.0",
        "attributes": {
            "permit_id": "MYPERMIT12345",
            "entity_name": "Ima Permit",
            "corp_num": "ABC12345",
            "permit_issued_date": "2018-01-01", 
            "permit_type": "ABC", 
            "permit_status": "OK", 
            "effective_date": "2019-01-01"
        }
    }
]
```

For example:

```bash
curl -H 'Content-Type: application/json' -X 'POST' http://localhost:5000/issue-credential -d @-
<paste contents of the above file here>
<CTRL-D>
```

This should return the ID numbers for the updated credentials, for example:

```
[
    {"result":"70273ab2-ca75-42cd-aef9-c16a968be49c", "success":true},
    {"result":"2f8986a7-9ba3-48ab-b34d-9cdf7759f5bc", "success":true},
    {"result":"822408b0-216a-4a51-b768-66436cd8130c", "success":true}
]
```

#### Submit Credentials via Bulk Load Script

Open a browser at http://localhost:5050 and:

- click on "initialization and load tasks" | "von data db init"
- click on "Run"
- then back to home page (left hand nav bar, click on "Overview")
- click on "von data event processor" then click on "Run"
- this will post about 360 random credentials
- then back to home page (left hand nav bar, click on "Overview")
- click on "von data pipeline status" then click on "Run"
- this will display the summary counts

If you navigate to the Credential Registry (http://localhost:8080) you can search for and view the loaded credentials.
