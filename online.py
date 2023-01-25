from google.protobuf.json_format import MessageToDict
import dm_pb2 as Danmaku
from xml.etree import ElementTree as ET
import requests
import re
import json

if __name__ == '__main__':
    print("输入视频地址")
    url_video = input()
    # 先创建xml树
    xml_root = ET.Element("comments")
    xml_root.text = "\n"
    headers = {
        'user-agent': 'Mozilla/5.0(Windows NT 10.0;Win64;x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36'
    }
    resp = requests.get(url=url_video, headers=headers)
    videoData_json = re.search(r"window.__INITIAL_STATE__=(?P<text>.*?);\(function\(\)", resp.text)
    # print(result['text'])
    videoData_dict = json.loads(videoData_json['text'])
    videoData = videoData_dict['videoData']['embedPlayer']

    oid = videoData['cid']
    avid = videoData['aid']

    url_com_dm = "https://api.bilibili.com/x/v2/dm/web/seg.so"
    i = 1  # 记录抓包索引
    j = 0  # 记录弹幕个数
    danmaku_seg = Danmaku.DmSegMobileReply()  # 定义protobuf
    danmaku_adv = 0  # 检测有没有高级弹幕，用于跳出循环

    while (1):
        # 先获取弹幕包
        params = {
            'type': '1', 'oid': oid, 'pid': avid, 'segment_index': str(i)
        }

        # 开始抓取
        resp = requests.get(url=url_com_dm, params=params)
        if (resp.text == ''):
            print('普通弹幕池抓取完成')  # 检测到空包后检查高级弹幕池
            url = 'http://api.bilibili.com/x/v2/dm/web/view'
            params = {
                'type': '1', 'oid': oid, 'pid': avid
            }
            resp = requests.get(url=url, params=params, headers=headers)
            danmaku_adv = Danmaku.DmWebViewReply()
            danmaku_adv.ParseFromString(resp.content)

            if (danmaku_adv.special_dms == []):
                print("无高级弹幕池")
                break  # 没有就跳出
            else:
                print("检测到高级弹幕池，开始抓取")
                url = danmaku_adv.special_dms[0]
                resp = requests.get(url=url, headers=headers)

        danmaku_seg.ParseFromString(resp.content)  # 读入弹幕包
        data_raw = MessageToDict(danmaku_seg)  # 转换为字典，其中elems后面就是对应的弹幕数据
        data_list = data_raw['elems']  # 返回的是一个数组+字典，先数组，数组里的字典

        # 样例:{'id': '1209963727210700800', 'progress': 7038, 'mode': 1,
        #     'fontsize': 25, 'color': 16777215, 'midHash': '3716354f',
        #     'content': '加油', 'ctime': '1671330116', 'weight': 1, 'idStr': '1209963727210700800'}
        #     <d p="7.03800,1,25,16777215,1671330116,0,3716354f,1209963727210700800,8">加油</d>
        # id对应弹幕id，与idStr一致，progress为播放毫秒数，除以1000就是秒，mode就是弹幕类型，fontsize字体大小
        # color颜色，midHash为发送用户哈希值，参照crc2mid，content为内容，ctime是发送时间戳，weigh屏蔽弹幕权重，

        for item in data_list:
            j += 1
            if (item.__contains__('progress')):
                playtime = str(item['progress'] / 1000)
            else:
                playtime = '0.000'
            if (item.__contains__('pool')):
                poolid = str(item['pool'])
            else:
                poolid = '0'
            if (item.__contains__('color')):
                color = str(item['color'])
            else:
                color = '0'
            if (item.__contains__('fontsize')):
                fontsize = str(item['fontsize'])
            else:
                fontsize = '25'
            # 弹幕写入xml
            comment = ET.SubElement(xml_root, "comment", {'id': item['id'], 'poolid': poolid, 'userhash': item['midHash'], 'sendtime': item['ctime']})
            comment_text = ET.SubElement(comment, "text")
            comment_text.text = item['content']
            ET.SubElement(comment, "attr", {'id': '0', 'playtime': playtime, 'mode': str(item['mode']), 'fontsize': fontsize, 'color': color})

        if (danmaku_adv != 0):
            print("高级弹幕池抓取完毕")
            # 说明普通池、高级弹幕池都抓完了，跳出循环
            break

        print(f"分包{i}抓取完毕")
        i += 1

    print(f"抓取完毕，共{j}条弹幕")
    print("输入保存的xml文件名")
    savepath = input()
    new_xml = ET.ElementTree(xml_root)
    new_xml.write(savepath, encoding='UTF-8', short_empty_elements=True)
