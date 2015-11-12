# vSphere REST API

This REST API utilizes the python SDK written by the VMware team and, using Flask, wraps the existing SOAP framework with RESTful calls. This framework also uses the tools found in the community samples the VMware team has also developed.

## Purpose
To provide a quick, easy, accurate route to creating vms. While this is only one cog in a machine, the point of this API is to provide a single target for devs to programaticly control vms without effecting the rest of the environment. As such, it is highly recommended that a separate resource pool is created called `api_vms`. The api will then search and target that pool for all vms created through it.

## Usage
Place the hostname (or ip) of the VCSA, an admin username, and it's password in a file named "config.json". These will be used for logging into the vCenter Server Appliance (VCSA).

## License
As VMware pyvmomi is under the Apache License V2, all code will follow this license.
