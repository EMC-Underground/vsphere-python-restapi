# vSphere REST API

This REST API utilizes the python SDK written by the VMware team and, using Flask, wraps the existing SOAP framework with RESTful calls. This framework also uses the tools found in the community samples the VMware team has also developed.

## Purpose
To provide a quick, easy, accurate route to creating vms. While this is only one cog in a machine, the point of this API is to provide a single target for devs to programaticly control vms without effecting the rest of the environment. As such, it is highly recommended that a separate resource pool is created called `api_vms`. The API will then search and target that pool for all vms created through it.

## Usage
You will need to set a few variables so the API can talk to the vCenter Server Appliance (VCSA).
### Locally
Run the following commands from your terminal. Note: you may need to use set instead of export, depending on your os.
```bash
export host=<Hostname or ip of the VCSA>
export username=<VCSA username>
export password=<Password for user>
python myapi.py
```
### In Cloud Foundry
Run the following commands, using your environment's info. If you changed the app name in the manifest, be sure to change it here too.
```bash
cf set-env labapi host <Hostname or ip of the VCSA>
cf set-env labapi username <VCSA username>
cf set-env labapi password <Password for user>
```
## License
As VMware pyvmomi is under the Apache License V2, all code will follow this license.
