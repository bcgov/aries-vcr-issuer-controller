[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

# Aries VCR - Issuer/Controller

This repository is a template for creating an [Aries](https://www.hyperledger.org/use/ARIES) Verifiable Credential Registry (VCR) Issuer Agent. [Aries VCR](https://github.com/bcgov/aries-vcr) is the foundational technology upon which the Government of British Columbia's [OrgBookBC](https://orgabook.gov.bc.ca) was built. Aries VCR Issuer Controller is a starter kit for building an Aries agent that issues verifiable credentials to instances of an Aries VCR, such as OrgBookBC. This repo contains code for an issuer controller that works with [Aries Cloud Agent Python](https://github.com/hyperledger/aries-cloudagent-python) (ACAPy) framework. The controller and an instance of ACA-Py can be deployed together to implement an Aries issuer agent.

`aries-vcr-issuer-controller` was developed as part of the Verifiable Organizations Network (VON). For more information on VON, visit https://vonx.io.  Even better, join in with what we are doing and contribute to VON and the [Trust over IP](trustoverip.org) community.

Still not sure what this is? Please see this [Getting started with VON](https://vonx.io/getting_started/get-started/) overview, paying particular attention to the `VON Issuer/Verifier Agent` section. That's what this repo implements.

## Terminology

### Aries VCR Issuer Controller or Agent

Aries Agents consist of two parts, a framework that handles all of the Aries agent type functions (e.g. messages, protocols, protocol state, agent storage, etc.) and a controller that provides the business logic that gives the agent personality. As such, we talk about the code in this repo as the Controller. When the controller code is deployed along with an instance of an agent framework&mdash;ACA-Py&mdash;we have an Aries VCR Issuer agent.  As such, in this repo we might talk about the code in this repo (the Aries VCR Issuer Controller), or talk about a deployed and running Aries VCR Issuer Agent.

Make sense?

### Aries VCR vs. OrgBook

A question we often get is what's the difference between OrgBook and Aries VCR? Here are the details.

The OrgBook is a specific instance of Aries VCR about registered organizations within a legal jurisdiction (e.g. province, state or nation). Each entity in an OrgBook is a registered organization (a corporation, a sole proprietorship, a co-op, a non-profit, etc.), and all of the verifiable credentials within an OrgBook repository relate to those registered organizations. 

So while OrgBook is an instance of the Aries VCR software, Aries VCR itself knows nothing about jurisdictions, registered organizations, etc. As a result can be used in many credential registry use cases. If the entities within an Aries VCR instance were doctors, then the verifiable credentials would all be about those doctors, and we'd have "DocBook". Same with engineers, lawyers, teachers, nurses and more. If an Aries VCR instance had construction sites as top level entities, the verifiable credentials would all be about those construction sites, such as permits, contractors, contracts, payments and so on.

Aries VCR knows about verifiable credentials, how to hold them, prove them and how to make the available for searching based on the values in the claims. What is in those credentials is up to the issuers that issue to that instance of an Aries VCR.

We often talk about the OrgBook being a repository of public credentials, and that OrgBook is publicly searchable. However, instances of Aries VCR do not have to contain public credentials and the website does not have to be publicly accessible. An organization could implement an instance of an Aries VCR, load it with with credentials containing proprietary data and wrap it with a mechanism to allow only authorized entities to access the data.

## Getting Started

Use this [Aries VCR Issuer Controller Getting Started Tutorial](GettingStartedTutorial.md) to go through the basics of configuring an Aries-VCR Issuer Agent created from this template.

## Configuration Guide

Much of the work in configuring an Aries VCR Issuer Agent is in setting up the YAML files in the [issuer_controller/config](issuer_controller/config) folder. A [Configuration Guide](issuer_controller/config/README.md) documents those files.

## Managing Your Controller Repo

If you are creating an agent for a service organization that will become an Aries VCR Issuer/Verifier agent, most of the changes you will make in this repo will be for your own organization's use and will not be pushed back into the base repo. As such, we suggest you use one of following methods for managing this repo. We recommend the first method, but would welcome suggestions of other approaches that might have more upside and less downside. Please add an issue to tell us about a better way.

1. Make a snapshot (not a fork or clone - a text copy) of this repo to use as the base repo for your organization's agent from there. The benefit of that approach is that your developers can fork the snapshot repo and manage everything through the common GitHub Pull Request (PR) model.  The downside is that periodically you should look for code updates to this ([aries-vcr-issuer-controller](https://github.com/bcgov/aries-vcr-issuer-controller)) repo and apply them to your copy. There are relatively easy ways to track such changes, such as keeping a fork of aries-vcr-issuer-controller, using GitHub's `compare` capability to find the differences and manually applying the relevant ones to your repo.

2. Make a fork of this repo, and in that, create a branch that you will use as the deployment branch for your agent instance. The benefit of this approach is that you can stay up-to-date with the base repo by applying commits to your branch from the `master`. The downside is a much more complex branching model for your developers and a non-typical deployment model for your code.

In theory, the two mechanisms above can be combined, and branches could be created in the main repo for the different agent instances. This might be an approach that, for example, the BC Gov could use&mdash;creating a branch for each OrgBookBC Issuer agent in BC Gov. However, we think that the benefits of such a scheme is not worth the complexity.

## Deploying Your Issuer Controller on OpenShift

When you are running locally, your issuer controller will automatically establish a connection between your agent and the OrgBook agent.  However when you deploy on OpenShift and connect to one of the OrgBook environments (dev, test or prod) this is not possible, and the agent connection must be established manually.

There are two steps:

1. Request an Invitation from the OrgBook agent: `/connections/create-invitation`

2. Receive this Invitation in your agent: `/connections/receive-invitation` - set the `alias` to `vcr-agent` (or whatever value you have set here: https://github.com/bcgov/aries-vcr-issuer-controller/blob/master/issuer_controller/config/services.yml#L340)

3. (There are 3 steps) (depending on your agent startup parameters) Accept this invitation through your agent `/connections/<conn_id>/accept-invitation`

4. (There are 4 steps) Verify your connection status

To test this process on your local installation, use the following startup command:

```bash
REGISTER_TOB_CONNECTION=false ./manage start
```

This will startup your Issuer Controller *without* an orgbook connection and you will need to follow the above steps.  Once the connection is established your Issuer will be registered with your local OrgBook.

## Getting Help or Reporting an Issue

To report bugs/issues/feature requests, please file an [issue](../../issues).

# How to Contribute

If you find this project helpful, please contribute back to the project. If you would like to contribute, please see our [CONTRIBUTING](./CONTRIBUTING.md) guidelines. Please note that this project is released with a [Contributor Code of Conduct](./CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.
