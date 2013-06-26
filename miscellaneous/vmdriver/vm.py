#!/usr/bin/env python
import lxml.etree as ET

# VM Instance class
class VMInstance:
    name = None
    vcpu = None
    cpu_share = None
    memory_max = None
    network_list = list()
    disk_list = list()
    context = dict()

class VMNetwork:
    ''' Virtual Machine network representing class
    name            -- network device name
    mac             -- the MAC address of the quest interface
    network_type    -- need to be "ethernet" by default
    model           -- available models in libvirt 
    QoS             -- CIRCLE QoS class?
    script          -- Executable network script /bin/true by default
    '''
    # Class attributes
    name = None
    network_type = None
    mac = None
    model = None
    QoS = None
    script_exec = '/bin/true'
    
    def __init__(self, name, mac, network_type='ethernet', model='virtio', QoS=None):
        self.name = name
        self.network_type = network_type
        self.mac = mac
        self.model = model
        self.QoS = QoS 
    
    # XML dump
    def dump_xml(self):
        xml_top = ET.Element('interface', attrib={'type' : self.network_type})
        ET.SubElement(xml_top, 'target', attrib={ 'dev' : self.name  })
        ET.SubElement(xml_top, 'mac', attrib={ 'address' : self.mac  })
        ET.SubElement(xml_top, 'model', attrib={ 'type' : self.model  })
        ET.SubElement(xml_top, 'script', attrib={ 'path' : self.script_exec  })
        return ET.tostring(xml_top, encoding='utf8', method='xml', pretty_print=True)


class VMDisk:
    disk_type = None
    disk_driver = None
    source = None
    target = None
    
    
a = VMNetwork(name="vm-77", mac="010101")
print a.dump_xml()
