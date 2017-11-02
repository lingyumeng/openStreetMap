# -*- coding:utf-8 -*-

import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = ["version", "changeset", "timestamp", "user", "uid"]

def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way":
        try:
            eid = element.attrib['id']
            node['id'] = eid
        except:
            return None

        node['type'] = element.tag
        node['visible'] = element.get('visible')
        created = dict()
        created['version'] = element.get('version')
        created['changeset'] = element.get('changeset')
        created['timestamp'] = element.get('timestamp')
        created['user'] = element.get('user')
        created['uid'] = element.get('uid')
        node['created'] = created

        pos = list()
        node_refs = list()
        if element.tag == "node":
            try:
                lat = float(element.get('lat'))
                lon = float(element.get('lon'))
                pos.append(lat)
                pos.append(lon)

            except ValueError:
                print('ERROR: transfer string to float error')
            node['pos'] = pos
        else:
            for subelement in element.findall('nd'):
                node_refs.append(subelement.get('ref'))
            node['node_refs'] = node_refs

        address = dict()
        address_flog = False
        names = dict()
        name_flog = False

        for subelement in element.findall('tag'):
            k = subelement.get('k')
            mproble = problemchars.search(k)
            if mproble:
                continue
            else:
                mcolon = lower_colon.search(k)
                if mcolon:
                    colonList = mcolon.group().split(":")
                    if colonList[0] == "addr":
                        address_flog = True
                        addr = colonList[1]
                        address[addr] = subelement.get('v')
                    elif colonList[0] == "name":
                        name_flog = True
                        name = colonList[1]
                        names[name] = subelement.get('v')
                    else:
                        otherType = colonList[1]
                        node[otherType] = subelement.get('v')
                else:
                    mlower = lower.search(k)
                    if mlower:
                        node[k] = subelement.get('v')
        if address_flog:
            node['address'] = address

        if name_flog:
            node['names'] = names

        return node
    else:
        return None

def process_map(file_in, pretty = False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")

    return data

def test():
    data = process_map('beijing_china.osm', False)
    pprint.pprint(data[0])

    for key,elem in data[0].items():
        if type(elem) != type([]) and type(elem) != type({}):
            if elem != None:
                elem = elem.encode('utf-8')
            print("{0} : {1}".format(key, elem))

        if type(elem) == type({}):
            print("{}: ".format(key))
            for subkey, subelem in elem.items():
                if type(subelem) != type([]) and type(subelem) != type({}):
                    if subelem != None and type(subelem) == type(u' '):
                        subelem = subelem.encode('utf-8')
                    print("    {0} : {1}, ".format(subkey,subelem))



    # correct_first_elem = {
    #     "id": "261114295",
    #     "visible": "true",
    #     "type": "node",
    #     "pos": [41.9730791, -87.6866303],
    #     "created": {
    #         "changeset": "11129782",
    #         "user": "bbmiller",
    #         "version": "7",
    #         "uid": "451048",
    #         "timestamp": "2012-03-28T18:31:23Z"
    #     }
    # }
    #
    # assert data[0] == correct_first_elem
    # assert data[-1]["address"] == {
    #                                 "street": "West Lexington St.",
    #                                 "housenumber": "1412"
    #                                   }
    # assert data[-1]["node_refs"] == [ "2199822281", "2199822390",  "2199822392", "2199822369",
    #                                 "2199822370", "2199822284", "2199822281"]
if __name__ == '__main__':
    test()

