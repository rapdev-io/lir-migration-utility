# PagerDuty to AIR Migration Tool

This tool is intended to assist in the migration from the PagerDuty platform
to the AIR platform. When executed, this tool will copy the following from PagerDuty
to AIR:
- Users
- Teams
- Services
- Schedules
- Escalation Policies

## Executing the Tool

### Modes
This tool can run in a `noop` mode and an `migrate` mode. `noop` will show you 
what will be created in AIR from PagerDuty, and `migrate` will actually 
create these objects in AIR.

### Requirements
- [PagerDuty API Key](https://support.pagerduty.com/docs/api-access-keys#section-generate-a-general-access-rest-api-key)
- AIR Access Key
- URL of AIR endpoint
- Docker and Docker Compose, or Python 3.9 (or greater)

### Setup
In the root of this repository, there is a file called `.env.example`. Rename this file
to `.env`, and replace the values of the file with your keys/url.

### Running with Docker Compose
The easiest way to run this code is via Docker Compose. From the root of the repo,
run:

```docker-compose build noop```
to build the container, followed by
```docker-compose run noop```
to execute the code in `noop` mode.

To run the migration, simply replace `noop` in the above command with `migrate`.

If you are developing against this repo, run `docker-compose run test` to run unit tests.

### Running with Python Locally
It is also possible to run this code without Docker. It is recommended to use a virtual
environment for this, if you chose this method.

From the root of this repository:
```python -m venv venv```
will build a virtual environment called `venv`. To activate it, run
```source venv/bin/activate```
You can now run the following to install the required packages to the virtual env:
```pip3 install -r requirements.txt```
Once packages are installed, you can run the following command (note: this assumes
that you have set your PagerDuty API key, AIR token, and AIR URL in your environment.
Replace environment variables here as necessary):
```
python3 -m cli.cli --pd $PAGERDUTY_API_KEY --irtoken $IRTOKEN --apiurl $AIRURL --noop
```
This will run the code in `noop` mode. In order to run the migration, remove the `--noop` flag.

## Caveats

There are some caveats to the operation of this tool that should be noted. Due to
AIR and PagerDuty being different tools, there are some operations that are performed
in this code that may be unexpected and should be noted.

- If a PagerDuty user does not have a last name, their last name in AIR will be a
  duplicate of their first name (as first and last are required in AIR). For example,
  if a PagerDuty user is just "Joe", they will become "Joe Joe" in AIR.
- If there are multiple managers for a PagerDuty team, one will be selected as the
  manager of the AIR team. A team in AIR can only have one manager.
- In AIR, a team should be associated with a service. If there is no team associated to
  a PagerDuty service, but the PagerDuty service has an escalation policy, a team
  will be inferred from the policy and assigned to the service in AIR. If a team
  and policy are NOT present on a PagerDuty team, the service will be created without
  a team, and the name of the service will reflect that.
- A PagerDuty schedule MUST have a team associated with it for the schedule to be
  migrated to AIR. If there is not a team associated, the schedule will not be created
  and a warning will be logged.
- For a PagerDuty schedule, if there is no end date, the end date in AIR will be set
  for 5 years in the future.
- Users in a PagerDuty schedule will only be added to an AIR schedule if they are part
  of the team associated with the schedule.
- Only PagerDuty escalations of type "user_reference" and "schedule_reference" can be 
  migrated to AIR. Any others will be ignored and logged as a warning.
- If no users for a PagerDuty escalation can be extracted from the team or schedule, it
  will be considered to not have an audience, and will not be created in AIR and will
  be logged as a warning.
