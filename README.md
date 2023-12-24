## About

![](https://raw.githubusercontent.com/Dagon-/ps-client/dev/images/demo.gif)

The parameter store client will

* Retrieve a list of parameter values in the target account
* Search for parameter names.
* Retrieve paramater values


## Passing credentials

ps-client uses AWS credentials.

A profile can be passed with the `--profile` switch and the region set with `--region`

If no profile is passed it will attempt to automatically detect credentials in the following order of precedence.

* Environment variables
* Shared credential file (~/.aws/credentials)

* AWS config file (~/.aws/config)

* Assume Role provider

## Usage

```
psclient

psclient --profile

psclient --region eu-west-1

psclient --profile test --region eu-west-1
