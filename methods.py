import atexit
import json
import os

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
from tools import tasks

vm_json_return=[]
import requests
import ssl

with open('config.json') as data_file:
    data = json.load(data_file)

host=data["host"]
user=data["username"]
pwd=data["password"]

requests.packages.urllib3.disable_warnings()

if os.getenv("VCAP_APP_PORT"):
    ssl._create_default_httpsi_context = ssl._create_unverified_context
    default_context = ssl._create_default_https_context

def hello():
    return "Why hello! I'm from another file!"

def server_connection():
    SI = None
    print host
    print user
    # Attempt to connect to the VCSA
    try:
        SI = connect.SmartConnect(host=host,user=user,pwd=pwd)
        atexit.register(connect.Disconnect, SI)
    except IOError, ex:
        pass

    if not SI:
        # TODO: change so that it throws an error but doesn't exit
        print "Unable to connect to host with supplied info."

    return SI 

"""
Python program for listing the vms on an ESX / vCenter host
"""
def debuger():
    try:
        service_instance = server_connection()
        content = service_instance.RetrieveContent()
        print "I got things..."
        a = content.rootFolder.childEntity[0].vmFolder.childEntity[1].childEntity[0].summary
	del vars(a.config)['product']
	fullData = vars(a.config)
	fullData.update(guest = vars(a.guest))
	fullData.update(storage = vars(a.storage))
	b = vars(a.runtime.host.summary.config.product)
	del vars(a.runtime.host.summary.config)['product']
	hostDetails = vars(a.runtime.host.summary.config)
        hostDetails.update(product = b)
        del hostDetails['featureVersion']
	fullData.update(host = hostDetails)
        return fullData
    except:
        return "I did not get things"

def print_vm_info(virtual_machine, depth=1):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    global vm_json_return
    maxdepth = 20
    vm_json = {}
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(virtual_machine, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = virtual_machine.childEntity
        for c in vmList:
            print_vm_info(c, depth + 1)
        return
    if hasattr(virtual_machine, 'vAppConfig'):
        if depth > maxdepth:
            return
        vmList = virtual_machine.childLink
        for c in vmList:
            print_vm_info(c, depth + 1)
        return

    summary = virtual_machine.summary
    if hasattr(summary.config, 'product'):
        del vars(summary.config)['product']
    vm_json_return.append(vars(summary.config))
    return

def get_all_vm_info():
    try:
        service_instance = server_connection()
        if service_instance is None:
	    print "Couldn't get the server instance"

        content = service_instance.RetrieveContent()
	for child in content.rootFolder.childEntity:
	    if hasattr(child, 'vmFolder'):
                datacenter = child
                vmFolder = datacenter.vmFolder
		vmList = vmFolder.childEntity
		for vm in vmList:
		    print_vm_info(vm)

            return vm_json_return

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

def find_vm_by_uuid(uuid):
    si = server_connection()
    search_index = si.content.searchIndex
    vm = search_index.FindByUuid(None, uuid, True, True)
    if vm is None:
        return {"not_found" : {"uuid":uuid}}
    a = vm.summary
    del vars(a.config)['product']
    del vars(a.runtime)['device']
    del vars(a.runtime)['offlineFeatureRequirement']
    del vars(a.runtime)['featureRequirement']
    fullData = vars(a.config)
    fullData.update(guest = vars(a.guest))
    fullData.update(storage = vars(a.storage))
    fullData.update({"overallStatus":a.overallStatus})
    fullData.update({"powerState":a.runtime.powerState})
    fullData.update({"bootTime":a.runtime.bootTime})
    b = vars(a.runtime.host.summary.config.product)
    del vars(a.runtime.host.summary.config)['product']
    hostDetails = vars(a.runtime.host.summary.config)
    hostDetails.update(product = b)
    del hostDetails['featureVersion']
    fullData.update(host = hostDetails)
    print a.quickStats
    return fullData

def delete_vm_from_server(uuid):
    #Get Server connection
    SI = server_connection()
    if SI is None:
        return "Unable to connect to server"

    search_index = SI.content.searchIndex
    if search_index is None:
        return "Unable to grab search index"

    #Find the vm to delete
    vm = search_index.FindByUuid(None, uuid, True, True)

    #Verify we have a vm
    if vm is None:
        return "Unable to locate VM with UUID of "+uuid

    # Ensure VM is powered off
    if format(vm.runtime.powerState) == "poweredOn":
        TASK = vm.PowerOffVM_Task()
	# TODO: verify that this does not cause a full app wait
	tasks.wait_for_tasks(SI, [TASK])
    
    #Destroy vm
    TASK = vm.Destroy_Task()
    tasks.wait_for_tasks(SI, [TASK])
    
    return "VM is destroyed"

def change_vm_stats(uuid):
    #Get server object
    SI = server_connection()

    #Find the vm to change
    VM = SI.content.searchIndex.FindByUuid(None, uuid, True, False)

    return "Function still in progress"

def create_new_vm(specs):
    """Creates a dummy VirtualMachine with 1 vCpu, 128MB of RAM.
    :param name: String Name for the VirtualMachine
    :param SI: ServiceInstance connection
    :param vm_folder: Folder to place the VirtualMachine in
    :param resource_pool: ResourcePool to place the VirtualMachine in
    :param datastore: DataStrore to place the VirtualMachine on
    """
    SI = server_connection()
    content = SI.RetrieveContent()
    datacenter = content.rootFolder.childEntity[0]
    vm_folder = datacenter.vmFolder
    hosts = datacenter.hostFolder.childEntity
    resource_pool = hosts[0].resourcePool
    datastore = specs['datastore']

    vm_name = specs['name']
    datastore_path = '[' + datastore + '] ' + vm_name

    # bare minimum VM shell, no disks. Feel free to edit
    vmx_file = vim.vm.FileInfo(logDirectory=None,
                               snapshotDirectory=None,
                               suspendDirectory=None,
                               vmPathName=datastore_path)

    config = vim.vm.ConfigSpec(name=specs['name'], memoryMB=long(specs['mem']),
                               numCPUs=int(specs['cpus']), files=vmx_file, 
			       guestId=specs['guestid'],
                               version=str(specs['vm_version']))

    print "Creating VM {}...".format(vm_name)
    task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
    tasks.wait_for_tasks(SI, [task])
           
    path = datastore_path + '/' + vm_name + '.vmx'
	           
    new_vm = content.searchIndex.FindByDatastorePath(datacenter, path)
    if new_vm is not None:
        a = new_vm.summary
	del vars(a.config)['product']
	del vars(a.runtime)['device']
	del vars(a.runtime)['offlineFeatureRequirement']
	del vars(a.runtime)['featureRequirement']
	fullData = vars(a.config)
	fullData.update(guest = vars(a.guest))
	fullData.update(storage = vars(a.storage))
	fullData.update({"overallStatus":a.overallStatus})
	fullData.update({"powerState":a.runtime.powerState})
	fullData.update({"bootTime":a.runtime.bootTime})
	b = vars(a.runtime.host.summary.config.product)
	del vars(a.runtime.host.summary.config)['product']
	hostDetails = vars(a.runtime.host.summary.config)
	hostDetails.update(product = b)
	del hostDetails['featureVersion']
	fullData.update(host = hostDetails)
	print a.quickStats
	return fullData
    else:
        return "Could not create vm"
