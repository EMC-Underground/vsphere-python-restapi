import atexit
import json

from pyVim import connect
from pyVmomi import vmodl
vm_json_return=[]
import requests
import ssl

requests.packages.urllib3.disable_warnings()
default_context = ssl._create_default_https_context
ssl._create_default_https_context = ssl._create_unverified_context

def hello():
    return "Why hello! I'm from another file!"

"""
Python program for listing the vms on an ESX / vCenter host
"""
def debuger(host,user,pwd):
    try:
        service_instance = connect.SmartConnect(host=host,
                                                user=user,
                                                pwd=pwd)

        atexit.register(connect.Disconnect, service_instance)

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

def get_all_vm_info(host,user,pwd):
    try:
        service_instance = connect.SmartConnect(host=host,
                                                user=user,
                                                pwd=pwd)

        atexit.register(connect.Disconnect, service_instance)

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

def find_vm_by_uuid(uuid,host,user,pwd):
    si = connect.SmartConnect(host=host, user=user, pwd=pwd)
    atexit.register(connect.Disconnect, si)
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
