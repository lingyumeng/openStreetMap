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

def clean_postcode(postcode):
    code = re.compile(r'^(\d{6}$)')
    postcode = postcode.rstrip()
    postcode = postcode.lstrip()

    mpostCode = code.search(postcode)
    if mpostCode:
        return mpostCode.group()
    else:
        return None

def clean_province(province):
    province = province.rstrip()
    province = province.lstrip()
    if province == u'北京' or province == u'河北省':
        return province
    else:
        province = u'北京'
        return province

# 清理非法城市信息
def clean_city(city):
    names = (u'北京', u'Beijing', u'北京市', u'beijing', u'Bejing', u'北京Beijing', u'北京市 Beijing')
    re_addr = re.compile(u"(^[\u4e00-\u9fa5]+)市([\u4e00-\u9fa5]+)区")

    city = city.rstrip()
    city = city.lstrip()

    mapping = dict()

    if city == u'涿州市' or city == u'大厂回族自治县':
        mapping['city'] = city
    elif city in names:
        mapping['city'] = '北京市'
    elif  city.find(u"区") > 0 and city.find(u"市") > 0:
        m_addr = re_addr.search(city)
        if m_addr:
            mapping['city'] = m_addr.group(1)+u'市'
            mapping['districtFromCity'] = m_addr.group(2)+u'区'
    elif city.find(u"区") > 0 or city.find(u"市") > 0:
        mapping['city'] = '北京市'

        district = city.decode('utf-8').replace(u'北京市', '')
        district = district.replace(u'北京', '')
        district = district.strip()
        mapping['districtFromCity'] = district
    elif city.find(u"北京") > 0:
        mapping['city'] = '北京市'
        district = city.decode('utf-8')
        district = district.replace(u"北京", '')
        district = district.strip()
        mapping['districtFromCity'] = district
    elif city.find('Beijing') > 0 or city.find('beijing') > 0:
        mapping['city'] = '北京市'
        district = city.replace("Beijing", '')
        district = city.replace("beijing", '')
        district = district.replace(',', '')
        district = district.strip()
        mapping['districtFromCity'] = district
    else:
        mapping['city'] = "北京市"
        mapping['districtFromCity'] = city

    return mapping

# 清理区县字段函数
def clean_district(district):
    district = district.lstrip()
    district = district.rstrip()
    cityAnddistrict = re.compile(u"(.*?)市([\u4e00-\u9fa5]+)区")

    map_district = {'Chaoyang': u"朝阳区", 'Dongcheng' : u"东城区", u"密云镇" : u"密云区", u"回龙观" : u"昌平区", u"大厂镇" : u"大厂回族自治县", u"上地南路":u"海淀区"}

    if district.find(u'市') > 0 and district.find(u'区'):
        mcidi = cityAnddistrict.search(district)
        if mcidi:
            district = mcidi.group(2)+u'区'
    elif district.find(u'市') == -1 and district.find(u'区'):
        if district.find(u"北京") > 0:
            district = district.replace(u'北京', '')
    elif district.find('District') > 0 or district.find('Qu'):
        district = district.replace('District', '')
        district = district.replace('Qu', '')
        district = district.strip()

        if map_district.has_key(district):
            district = map_district[district]
    else:
        if map_district.has_key(district):
            district = map_district[district]

    return district

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
            for subelement in element.findall('nd'):        #处理nd子标签
                node_refs.append(subelement.get('ref'))
            node['node_refs'] = node_refs

        # 定义地址字典、地址写入标志、各语言地名字典、地名字典写入标志
        address = dict()
        address_flog = False
        names = dict()
        name_flog = False

        # 处理tag子标签
        for subelement in element.findall('tag'):
            k = subelement.get('k')                                          # 获取tag标签k属性
            mproble = problemchars.search(k)                                 # 检查k属性是否有问题
            if mproble:
                continue
            else:
                mcolon = lower_colon.search(k)                               # 检查k属性是否包含冒号
                if mcolon:
                    colonList = mcolon.group().split(":")
                    if colonList[0] == "addr":                              # 检查是否为地址段标签
                        address_flog = True
                        addr = colonList[1]                                  # 获取相关地址信息名称
                        address[addr] = subelement.get('v')                 # 获取相关地址信息值

                        if addr == 'postcode':                               # 清理非法邮政编码
                            address[addr] = clean_postcode(address[addr])
                        elif addr == 'province':                             # 清理非法省份信息
                            address[addr] = clean_province(address[addr])
                        elif addr == 'city':                                  # 清理非法城市信息
                            mapping = clean_city(address[addr])
                            if mapping.has_key('city'):
                                address[addr] = mapping['city']

                            if mapping.has_key('districtFromCity'):
                                address['districtFromCity'] = mapping['districtFromCity']

                        elif addr == 'district':                              # 清理非法区字段信息
                            address[addr] = clean_district(address[addr])

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
    file_out = "cleaned_{0}.json".format(file_in)
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


if __name__ == '__main__':
    test()

