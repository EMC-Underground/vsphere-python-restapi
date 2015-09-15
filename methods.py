import atexit
import tools.cli as cli
import json

from pyVim import connect
from pyVmomi import vmodl


def hello():
    return "Why hello! I'm from another file!"

"""
Python program for listing the vms on an ESX / vCenter host
"""

def print_vm_info(virtual_machine, depth=1):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    maxdepth = 10
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

    summary = virtual_machine.summary
    if not hasattr(summary.config, 'name'):
        return

    vm_json.update({"Name":summary.config.name})
    vm_json.update({"UUID":summary.config.instanceUuid})


    return vm_json

def get_all_vm_info(host,user,pwd):
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    args = cli.get_args()
    port = 443
    vm_json_return = []
    try:
        service_instance = connect.SmartConnect(host=host,
                                                user=user,
                                                pwd=pwd)

        atexit.register(connect.Disconnect, service_instance)

        content = service_instance.RetrieveContent()
        children = content.rootFolder.childEntity
        for child in children:
            if hasattr(child, 'vmFolder'):
                datacenter = child
            else:
                # some other non-datacenter type object
                continue

            vm_folder = datacenter.vmFolder
            vm_list = vm_folder.childEntity
            for virtual_machine in vm_list:
                #print_vm_info(virtual_machine, 10)
                #Test return
                vm_json = print_vm_info(virtual_machine, 10)
                if vm_json is not None: 
                    vm_json_return.append(vm_json) 
            
            return json.dumps(vm_json_return)

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return -1

    return 0

def find_vm_by_uuid(uuid,host,user,pwd):
    # form a connection...
    si = connect.SmartConnect(host=host, user=user, pwd=pwd)

    # doing this means you don't need to remember to disconnect your script/objects
    atexit.register(connect.Disconnect, si)

    # see:
    # http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.ServiceInstanceContent.html
    # http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
    search_index = si.content.searchIndex
    vm = search_index.FindByUuid(None, uuid, True, True)

    if vm is None:
#        print("Could not find virtual machine '{0}'".format(uuid))
        return "VM NOT FOUND"

#    print("Found Virtual Machine")
    details = {'name': vm.summary.config.name,
               'bios UUID': vm.summary.config.uuid,
               'path to VM': vm.summary.config.vmPathName,
               'guest OS id': vm.summary.config.guestId,
               'guest OS name': vm.summary.config.guestFullName,
               'host name': vm.runtime.host.name,
               'last booted timestamp': vm.runtime.bootTime,
               }
    return json.dumps(details)
#    for name, value in details.items():
#        print("{0:{width}{base}}: {1}".format(name, value, width=25, base='s'))
