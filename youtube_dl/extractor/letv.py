# coding: utf-8
from __future__ import unicode_literals

import os.path
import re
import time
import datetime

from .common import InfoExtractor
from ..compat import (compat_urlparse, compat_urllib_parse)
from ..utils import (ExtractorError, parse_iso8601)


class LetvIE(InfoExtractor):
    _VALID_URL = r'http://www\.letv\.com/ptv/vplay/(?P<id>\d+).html'

    _TESTS = [{
        'url': 'http://www.letv.com/ptv/vplay/22005890.html',
        'md5': 'cab23bd68d5a8db9be31c9a222c1e8df',
        'info_dict': {
            'id': '22005890',
            'ext': 'mp4',
            'title': '第87届奥斯卡颁奖礼完美落幕 《鸟人》成最大赢家',
            'timestamp': 1424747397,
            'upload_date': '20150224',
        }
    }, {
        'url': 'http://www.letv.com/ptv/vplay/1118082.html',
        'info_dict': {
            'id': '1118082',
            'ext': 'mp4',
        }
    }]

    @staticmethod
    def urshift(val, n):
        return val >> n if val >= 0 else (val + 0x100000000) >> n

    # ror() and calcTimeKey() are reversed from a embedded swf file in KLetvPlayer.swf
    def ror(self, param1, param2):
        _loc3_ = 0
        while _loc3_ < param2:
            param1 = self.urshift(param1, 1) + ((param1 & 1) << 31)
            _loc3_ += 1
        return param1

    def calcTimeKey(self, param1):
        _loc2_ = 773625421
        _loc3_ = self.ror(param1, _loc2_ % 13)
        _loc3_ = _loc3_ ^ _loc2_
        _loc3_ = self.ror(_loc3_, _loc2_ % 17)
        return _loc3_

    def _real_extract(self, url):
        media_id = self._match_id(url)
        page = self._download_webpage(url, media_id)
        params = {
            'id': media_id,
            'platid': 1,
            'splatid': 101,
            'format': 1,
            'tkey': self.calcTimeKey(int(time.time())),
            'domain': 'www.letv.com'
        }
        play_json = self._download_json(
            'http://api.letv.com/mms/out/video/playJson?' + compat_urllib_parse.urlencode(params),
            media_id, 'playJson data')

        # Check for errors
        playstatus = play_json['playstatus']
        if playstatus['status'] == 0:
            flag = playstatus['flag']
            if flag == 1:
                msg = 'Country %s auth error' % playstatus['country']
            else:
                msg = 'Generic error. flag = %d' % flag
            raise ExtractorError(msg, expected=True)

        playurl = play_json['playurl']

        formats = ['350', '1000', '1300', '720p', '1080p']
        dispatch = playurl['dispatch']

        urls = []
        for format_id in formats:
            if format_id in dispatch:
                media_url = playurl['domain'][0] + dispatch[format_id][0]

                # Mimic what flvxz.com do
                url_parts = list(compat_urlparse.urlparse(media_url))
                qs = dict(compat_urlparse.parse_qs(url_parts[4]))
                qs.update({
                    'platid': '14',
                    'splatid': '1401',
                    'tss': 'no',
                    'retry': 1
                })
                url_parts[4] = compat_urllib_parse.urlencode(qs)
                media_url = compat_urlparse.urlunparse(url_parts)

                url_info_dict = {
                    'url': media_url,
                    'ext': os.path.splitext(dispatch[format_id][1])[1][1:]
                }

                if format_id[-1:] == 'p':
                    url_info_dict['height'] = format_id[:-1]

                urls.append(url_info_dict)

        publish_time = parse_iso8601(self._html_search_regex(
            r'发布时间&nbsp;([^<>]+) ', page, 'publish time', fatal=False),
            delimiter=' ', timezone=datetime.timedelta(hours=8))

        return {
            'id': media_id,
            'formats': urls,
            'title': playurl['title'],
            'thumbnail': playurl['pic'],
            'timestamp': publish_time,
        }


class LetvTvIE(InfoExtractor):
    _VALID_URL = r'http://www.letv.com/tv/(?P<id>\d+).html'
    _TESTS = [{
        'url': 'http://www.letv.com/tv/46177.html',
        'info_dict': {
            'id': '46177',
            'title': '美人天下',
            'description': 'md5:395666ff41b44080396e59570dbac01c'
        },
        'playlist_count': 35
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        page = self._download_webpage(url, playlist_id)

        media_urls = list(set(re.findall(
            r'http://www.letv.com/ptv/vplay/\d+.html', page)))
        entries = [self.url_result(media_url, ie='Letv')
                   for media_url in media_urls]

        title = self._html_search_meta('keywords', page, fatal=False).split('，')[0]
        description = self._html_search_meta('description', page, fatal=False)

        return self.playlist_result(entries, playlist_id, playlist_title=title,
                                    playlist_description=description)


class LetvPlaylistIE(LetvTvIE):
    _VALID_URL = r'http://tv.letv.com/[a-z]+/(?P<id>[a-z]+)/index.s?html'
    _TESTS = [{
        'url': 'http://tv.letv.com/izt/wuzetian/index.html',
        'info_dict': {
            'id': 'wuzetian',
            'title': '武媚娘传奇',
            'description': 'md5:e12499475ab3d50219e5bba00b3cb248'
        },
        'playlist_count': 96
    }, {
        'url': 'http://tv.letv.com/pzt/lswjzzjc/index.shtml',
        'info_dict': {
            'id': 'lswjzzjc',
            # should be "劲舞青春", but I can't find a simple way to determine
            # the playlist title
            'title': '乐视午间自制剧场',
            'description': 'md5:b1eef244f45589a7b5b1af9ff25a4489'
        },
        'playlist_mincount': 7
    }]
