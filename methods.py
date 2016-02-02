# All imports used for the whole program

import atexit
import os
import requests
import ssl
import sys

from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
from tools import tasks

# Pull in the config info used to create connections to the vshpere host
try:
    host = os.environ['host']
except KeyError:
    print('ERROR: The $host env var hasn\'t been set. Please set it with "export host=<ip>" or "set host=<ip>", '
        'depending on the OS')
    sys.exit(1)

try:
    user = os.environ['username']
except KeyError:
    print('ERROR: The ${0} env var hasn\'t been set. Please set it with "export {0}=<{0}>" or '
          '"set {0}=<{0}>", depending on the OS'.format('username'))
    sys.exit(1)

try:
    pwd = os.environ['password']
except KeyError:
    print('ERROR: The ${0} env var hasn\'t been set. Please set it with "export {0}=<{0}>" or '
          '"set {0}=<{0}>", depending on the OS'.format('password'))
    sys.exit(1)

# Get the resource pool name or use default
resource_pool_name = os.getenv('resource_pool','api_vms')
vm_folder_name = os.getenv('vm_folder', 'api_vm_folder')
default_network_name = os.getenv('network', 'VM Network')

# This allows the API to work in corp environments
requests.packages.urllib3.disable_warnings()

# Check if the env is CF, and set the needed CF env vars
if os.getenv("PORT"):
    print ("you are running in CF")
    default_context = ssl._create_default_https_context
    ssl._create_default_https_context = ssl._create_unverified_context


def debugger():
    return os.getenv("VCAP_APP_PORT")

# Create a connection to the vcsa


def server_connection():
    # Attempt to connect to the VCSA
    import ssl
    try:
        SI = connect.SmartConnect(host=host,
                                    user=user,
                                    pwd=pwd,
                                    #sslContext=context
                                  )
    except requests.exceptions.SSLError as e:
        print("Falling back to no verification for SSL")

        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_NONE
        SI = connect.SmartConnect(host=host,
                                    user=user,
                                    pwd=pwd,
                                    sslContext=context
                              )

    print("Made the connection")
    atexit.register(connect.Disconnect, SI)
    return SI

# Helper function to so the actually traversal and printing of the vms.
# Includes templates


def print_vm_info(virtual_machine, depth=1, full_vm_list=None):
    """
    Print information for a particular virtual machine or recurse into a
    folder with depth protection
    """
    maxdepth = 20
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(virtual_machine, 'childEntity'):
        if depth > maxdepth:
            return
        vmList = virtual_machine.childEntity
        for c in vmList:
            print_vm_info(c, depth + 1, full_vm_list)
        return
    if hasattr(virtual_machine, 'vAppConfig'):
        if depth > maxdepth:
            return
        vmList = virtual_machine.childLink
        for c in vmList:
            print_vm_info(c, depth + 1, full_vm_list)
        return

    summary = virtual_machine.summary
    if hasattr(summary.config, 'product'):
        del vars(summary.config)['product']
    if summary.config.template is False:
        full_vm_list.append(vars(summary.config))
    return

# Root function for get a full list of vms


def get_all_vm_info():
    try:
        service_instance = server_connection()
        if service_instance is None:
            print ("Couldn't get the server instance")
        full_vm_list = []
        content = service_instance.RetrieveContent()
        for child in content.rootFolder.childEntity:
            if hasattr(child, 'vmFolder'):
                datacenter = child
                vmFolder = datacenter.vmFolder
                vmList = vmFolder.childEntity
                for vm in vmList:
                    print_vm_info(vm, 1, full_vm_list)

        return full_vm_list

    except vmodl.MethodFault as error:
        print ("Caught vmodl fault : {0}".format(error.msg))
        return -1

    return 0

# Helper function to print a short list of vm details


def print_short_detail_list(vm):
    vm_summary = vm.summary
    a = vm_summary
    del vars(a.config)['product']
    del vars(a.runtime)['device']
    del vars(a.runtime)['offlineFeatureRequirement']
    del vars(a.runtime)['featureRequirement']
    fullData = vars(a.config)
    del vars(a.guest)['guestId']
    fullData.update(guest=vars(a.guest))
    fullData.update(storage=vars(a.storage))
    fullData.update({"overallStatus": a.overallStatus})
    fullData.update({"powerState": a.runtime.powerState})
    fullData.update({"bootTime": a.runtime.bootTime})

    # Grab the tags from vm.config
    tags = {}
    for opts in vm.config.extraConfig:
        if opts.key == "Language":
            tags.update({opts.key: opts.value})
        elif opts.key == "User":
            tags.update({opts.key: opts.value})
        elif opts.key == "Application":
            tags.update({opts.key: opts.value})
    fullData.update({"extraConfig": tags})

    b = vars(a.runtime.host.summary.config.product)
    del vars(a.runtime.host.summary.config)['product']
    hostDetails = vars(a.runtime.host.summary.config)
    hostDetails.update(product=b)
    del hostDetails['featureVersion']
    fullData.update(host=hostDetails)
    return fullData

# Find a specific vm based on the instance UUID


def find_vm_by_uuid(UUID):
    vm = fetch_vm(UUID)
    if vm is None:
            return {"not_found": {"uuid": uuid}}
    return print_short_detail_list(vm)
# Fetch a VM by either UUID

def fetch_vm(UUID):
    si = server_connection()
    search_index = si.content.searchIndex
    uuid = UUID.lower()
    vm = search_index.FindByUuid(None, uuid, True, True)
    if vm is None:
        vm = search_index.FindByUuid(None, uuid, True, False)
    return vm
# Delete a vm from the server based on the uuid


def delete_vm_from_server(uuid):
    # Get Server connection
    SI = server_connection()
    if SI is None:
        return "Unable to connect to server"

    search_index = SI.content.searchIndex
    if search_index is None:
        return "Unable to grab search index"

    # Find the vm to delete
    vm = fetch_vm(uuid)

    # Verify we have a vm
    if vm is None:
        return "Unable to locate VM with UUID of " + uuid

    # Ensure VM is powered off
    if format(vm.runtime.powerState) == "poweredOn":
        TASK = vm.PowerOffVM_Task()
        # TODO: verify that this does not cause a full app wait
        tasks.wait_for_tasks(SI, [TASK])

    # Destroy vm
    TASK = vm.Destroy_Task()
    tasks.wait_for_tasks(SI, [TASK])

    return "VM is destroyed"

# Change the stats of a vm based on the uuid. Currently can only change
# the cpu and memory


def change_vm_stats(uuid, specs):
    # Get server object
    SI = server_connection()

    # Find the vm to change
    VM = fetch_vm(uuid)
    if VM is None:
        return "Couldn't find VM with UUID " + uuid

    if 'cpu' in specs:
        task = VM.ReconfigVM_Task(vim.vm.ConfigSpec(numCPUs=int(specs['cpu'])))
        tasks.wait_for_tasks(SI, [task])

    if 'mem' in specs:
        task = VM.ReconfigVM_Task(
            vim.vm.ConfigSpec(memoryMB=long(specs['mem'])))
        tasks.wait_for_tasks(SI, [task])

    if 'vm_broker' in specs:
        config = vim.vm.ConfigSpec()
	opt = vim.option.OptionValue()
	options_values = {}
	options_values.update({"vm_broker": specs['vm_broker']})
	for k, v in options_values.iteritems():
            opt.key = k
            opt.value = v
            config.extraConfig.append(opt)
            opt = vim.option.OptionValue()
	task = VM.ReconfigVM_Task(config)
	tasks.wait_for_tasks(SI, [task])

    return "I fixed it!"

# Helper function to add a netowrk connection to a vm


def add_network(vm, si, content, netName):
    spec = vim.vm.ConfigSpec()
    dev_changes = []
    network_spec = vim.vm.device.VirtualDeviceSpec()
    network_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    network_spec.device = vim.vm.device.VirtualVmxnet3()
    print("Getting a network...")
    # Get network type
    for net in content.rootFolder.childEntity[0].network:
        if net.name == netName:
            if isinstance(net, vim.dvs.DistributedVirtualPortgroup):
                # Run portgroup code
                pg_obj = get_obj(
                    content, [vim.dvs.DistributedVirtualPortgroup], netName)
                dvs_port_connection = vim.dvs.PortConnection()
                dvs_port_connection.portgroupKey = pg_obj.key
                dvs_port_connection.switchUuid = pg_obj.config.distributedVirtualSwitch.uuid
                network_spec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                network_spec.device.backing.port = dvs_port_connection
                break
            elif isinstance(net, vim.Network):
                # Run plain network code
                network_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                network_spec.device.backing.network = get_obj(
                    content, [vim.Network], netName)
                network_spec.device.backing.deviceName = netName
                break
        else:
            print("This name is not a network")

    # Allow the network card to be hot swappable
    network_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    network_spec.device.connectable.startConnected = True
    network_spec.device.connectable.allowGuestControl = True

    dev_changes.append(network_spec)
    spec.deviceChange = dev_changes
    task = []
    task.append(vm.ReconfigVM_Task(spec=spec))
    tasks.wait_for_tasks(si, task)

# Helper function to get an object refernce


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)

    for view in container.view:
        if view.name == name:
            obj = view
            break
    return obj

# Helper function to create a scsi controller for a vm


def create_scsi_controller(vm, si):
    spec = vim.vm.ConfigSpec()
    dev_changes = []
    controller_spec = vim.vm.device.VirtualDeviceSpec()
    controller_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    controller_spec.device = vim.vm.device.VirtualLsiLogicController()
    controller_spec.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
    dev_changes.append(controller_spec)
    spec.deviceChange = dev_changes
    task = []
    task.append(vm.ReconfigVM_Task(spec=spec))
    tasks.wait_for_tasks(si, task)
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
            print("Found our controller")
            return dev

# Helper function to add a disk to a vm


def add_disk(vm, si, disk_size=30):
    spec = vim.vm.ConfigSpec()
    unit_number = 0
    controller = None
    # get all disks on a VM, set unit_number to the next available
    for dev in vm.config.hardware.device:
        if hasattr(dev.backing, 'fileName'):
            unit_number = int(dev.unitNumber) + 1
            # unit_number 7 reserved for scsi controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                print "we don't support this many disks"
                return
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
            controller = dev
            print("We have a controller")
    # add disk here
    dev_changes = []
    new_disk_kb = int(disk_size) * 1024 * 1024
    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
    disk_spec.device.backing.thinProvisioned = True
    disk_spec.device.backing.diskMode = 'persistent'
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.capacityInKB = new_disk_kb
    if controller is None:
        print "Creating new controller"
        controller = create_scsi_controller(vm, si)
    disk_spec.device.controllerKey = controller.key
    dev_changes.append(disk_spec)
    spec.deviceChange = dev_changes
    vm.ReconfigVM_Task(spec=spec)

# Core create vm function that handles generating all the neccasary part


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
    datastore = specs['datastore']

    print("Finding the resource pool")
    # Find the api resource pool
    datacenters = content.rootFolder.childEntity
    loopbreak = False
    for dc in datacenters:
        for host in dc.hostFolder.childEntity:
            for pool in host.resourcePool.resourcePool:
                if pool.name == resource_pool_name:
                    resource_pool = pool
                    datacenter = dc
                    print("Got the resource pool and dc...")
                    loopbreak = True
                    break
            if loopbreak:
                break
        if loopbreak:
            break

    # Find the api vm folder
    for folder in datacenter.vmFolder.childEntity:
        if folder.name == vm_folder_name:
            print("Got the vm folder...")
            vm_folder = folder
            break

    vm_name = specs['name']
    datastore_path = '[' + datastore + '] ' + vm_name

    # bare minimum VM shell creation
    vmx_file = vim.vm.FileInfo(logDirectory=None, snapshotDirectory=None, suspendDirectory=None,
                               vmPathName=datastore_path)

    config = vim.vm.ConfigSpec(name=specs['name'], memoryMB=long(specs['mem']),
                               numCPUs=int(specs['cpus']), files=vmx_file,
                               guestId=specs['guestid'], version=str(specs['vm_version']))

    # Add custom tags
    config.extraConfig = []
    opt = vim.option.OptionValue()
    options_values = {}
    # if hasattr(specs, "user"):
    if 'user' in specs:
        print("Got user: {0}".format(specs['user']))
        options_values.update({"User": specs['user']})
    # if hasattr(specs, "language"):
    if 'language' in specs:
        print("Got language: {0}".format(specs['language']))
        options_values.update({"Language": specs['language']})
    if 'application' in specs:
        print("Got application: {0}".format(specs['application']))
        options_values.update({"Application": specs['application']})

    for k, v in options_values.iteritems():
        opt.key = k
        opt.value = v
        config.extraConfig.append(opt)
        opt = vim.option.OptionValue()

    # Send off creeation task
    print("Creating VM {0}...".format(vm_name))
    task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
    print("Sending to the text manager")
    tasks.wait_for_tasks(SI, [task])
    print("Done...now to find it...")
    path = datastore_path + '/' + vm_name + '.vmx'

    # Verify the shell was created
    new_vm = content.searchIndex.FindByDatastorePath(datacenter, path)
    if new_vm is not None:
        # Now that the vm shell is created, add a disk to it
        # If the user requested a specific size, use that, otherwise use
        # default
        print("Found it...now adding a disk...")
        if hasattr(specs, 'disk_size'):
            add_disk(vm=new_vm, si=SI, disk_size=specs['disk_size'])
        else:
            add_disk(vm=new_vm, si=SI)

        # Add a network to the vm
        print("...adding the network...")
        if 'network' in specs:
            add_network(new_vm, SI, content, specs['network'])
        else:
            add_network(new_vm, SI, content, default_network_name)

        # Power on the vm
        print("...and powering it on!")
        new_vm.PowerOnVM_Task()

        # Respond with the vm summary
        return print_short_detail_list(new_vm)
    else:
        return "Could not create vm"

# Function to get a single attribute of a vm


def get_vm_attribute(uuid, attr, root_attr = None):
    print("Searching for {0} in {1}".format(attr, uuid))
    vmStats = find_vm_by_uuid(uuid)
    return_value = "null"
    break_var = False
    print("Entering Core attrs")
    for key1, value1 in vmStats.iteritems():
        print("key is {0}".format(key1))
        if key1.lower() == attr.lower():
            return_value = value1
            break_var = True

        if key1 == "extraConfig":
            print("Searching in {0}".format(key1))
            for key2, value2 in value1.iteritems():
                if key2.lower() == attr.lower():
                    return_value = value2
                    break_var = True

        if key1 == "guest":
            print("Searching in {0}".format(key1))
            for key2, value2 in value1.iteritems():
                if key2.lower() == attr.lower():
                    return_value = value2
                    break_var = True

        elif key1 == "host" and root_attr == "host":
            print("Searching in {0}".format(key1))
            for key2, value2 in value1.iteritems():
                if key2.lower() == attr.lower():
                    return_value = value2
                    break_var = True

                if break_var:
                    break

        elif key1 == "storage":
            print("Searching in {0}".format(key1))
            for key2, value2 in value1.iteritems():
                if key2.lower() == attr.lower():
                    return_value = value2
                    break_var = True
        if break_var:
            break

    return str(return_value)

# Function to force a VM with specified UUID to PXE boot


def force_pxe_boot(uuid, specs):
    SI = server_connection()

    # Find the vm to change
    VM = fetch_vm(uuid)
    if VM is None:
        return "Couldn't find VM with UUID " + uuid

    if 'guestid' in specs:
        # Change the guestid
        task = VM.ReconfigVM_Task(vim.vm.ConfigSpec(guestId=specs['guestid']))
        tasks.wait_for_tasks(SI, [task])

        # Determine the network being used
        if 'network' in specs:
            netName = specs['network']
        else:
            netName = default_network_name

        # Get the vm's network device's id
        netKey = None
        for device in VM.config.hardware.device:
            if hasattr(device.backing, 'deviceName'):
                if device.backing.deviceName == netName:
                    netKey = int(device.key)
                    break

        # Verify the network was Found
        if netKey is None:
            return "Couldn't find the network adapter."

        # Set vm to PXE boot
        task = VM.PowerOffVM_Task()
        tasks.wait_for_tasks(SI, [task])
        pxedevice = vim.vm.BootOptions.BootableEthernetDevice(deviceKey = netKey)
        pxeboot = vim.vm.BootOptions(bootOrder = [pxedevice])
        task = VM.ReconfigVM_Task(vim.vm.ConfigSpec(bootOptions = pxeboot))
        tasks.wait_for_tasks(SI, [task])
        task = VM.PowerOnVM_Task()
	tasks.wait_for_tasks(SI, [task])

	return "Your vm will now be PXEboot with a guestid of {0}".format(specs['guestid'])

    else:
        return "No guestid was specified in packet."
